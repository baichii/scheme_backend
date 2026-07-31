import asyncio
from dataclasses import dataclass
from datetime import datetime

from backend.engine.client import EngineClientMode
from backend.engine.schemas import (
    EngineAgentEventDispatchMessage,
    EngineCreateRequest,
    EngineEventRecord,
    EngineLogDispatchMessage,
    EngineQueryRequest,
    EngineResponse,
    EngineSimTimeMessage,
    EngineStateChange,
    EngineStateDispatchMessage,
    EngineStopRequest,
    EngineTaskDefinition,
    EngineTaskState,
)


@dataclass
class _FakeTaskRecord:
    definition: EngineTaskDefinition
    state: EngineTaskState
    runner: asyncio.Task[None] | None = None


class FakeEngineClient:
    mode = EngineClientMode.FAKE

    def __init__(
        self,
        *,
        pending_seconds: float = 0.1,
        task_duration_seconds: float = 10.0,
        stopping_seconds: float = 0.1,
        log_interval_seconds: float = 1.0,
        sim_time_interval_seconds: float = 1.0,
    ) -> None:
        if pending_seconds < 0 or task_duration_seconds < 0 or stopping_seconds < 0:
            raise ValueError("Fake engine lifecycle durations cannot be negative")
        if log_interval_seconds <= 0 or sim_time_interval_seconds <= 0:
            raise ValueError("Fake engine log and sim-time intervals must be greater than zero")

        self._pending_seconds = pending_seconds
        self._task_duration_seconds = task_duration_seconds
        self._stopping_seconds = stopping_seconds
        self._log_interval_seconds = log_interval_seconds
        self._sim_time_interval_seconds = sim_time_interval_seconds
        self._tasks: dict[str, _FakeTaskRecord] = {}
        self._events: list[EngineEventRecord] = []
        self._sim_runners: set[asyncio.Task[None]] = set()
        self._next_sequence = 1
        self._lock = asyncio.Lock()
        self._closed = False

    async def create(self, request: EngineCreateRequest) -> EngineResponse[str]:
        task_ids = [task.id for task in request.body]
        if len(task_ids) != len(set(task_ids)):
            return EngineResponse(code=400, data="", error_info="Duplicate task IDs in create request")

        async with self._lock:
            if self._closed:
                return EngineResponse(code=400, data="", error_info="Fake engine client is closed")

            existing_ids = [task_id for task_id in task_ids if task_id in self._tasks]
            if existing_ids:
                return EngineResponse(
                    code=400,
                    data="",
                    error_info=f"Task IDs already exist: {', '.join(existing_ids)}",
                )

            for definition in request.body:
                stored_definition = definition.model_copy(deep=True)
                record = _FakeTaskRecord(
                    definition=stored_definition,
                    state=EngineTaskState.READY,
                )
                self._tasks[definition.id] = record
                self._append_state_event_locked(record)

            for task_id in task_ids:
                self._tasks[task_id].runner = asyncio.create_task(
                    self._run_lifecycle(task_id),
                    name=f"fake-engine-{task_id}",
                )

            if task_ids:
                deduce_id = request.body[0].biz_value.deduce_id
                self._append_sim_time_event_locked(request.body[0], deduce_id)
                sim_runner = asyncio.create_task(
                    self._run_sim_time(task_ids, request.body[0], deduce_id),
                    name=f"fake-engine-sim-time-{deduce_id or task_ids[0]}",
                )
                self._sim_runners.add(sim_runner)
                sim_runner.add_done_callback(self._sim_runners.discard)

        return EngineResponse(code=200, data="", error_info="")

    async def query(
        self,
        request: EngineQueryRequest,
    ) -> EngineResponse[dict[str, EngineTaskState]]:
        async with self._lock:
            states = {
                task_id: self._tasks[task_id].state if task_id in self._tasks else EngineTaskState.UNKNOWN
                for task_id in request.body
            }
        return EngineResponse(code=200, data=states, error_info="")

    async def stop(self, request: EngineStopRequest) -> EngineResponse[dict]:
        cancelled_runners: list[asyncio.Task[None]] = []
        async with self._lock:
            for task_id in dict.fromkeys(request.body):
                record = self._tasks.get(task_id)
                if record is None or record.state in {
                    EngineTaskState.STOPPING,
                    EngineTaskState.END,
                    EngineTaskState.ERROR,
                }:
                    continue

                if record.runner is not None and not record.runner.done():
                    record.runner.cancel()
                    cancelled_runners.append(record.runner)

                record.state = EngineTaskState.STOPPING
                self._append_state_event_locked(record)
                record.runner = asyncio.create_task(
                    self._finish_stopping(task_id),
                    name=f"fake-engine-stop-{task_id}",
                )

        if cancelled_runners:
            await asyncio.gather(*cancelled_runners, return_exceptions=True)
        return EngineResponse(code=200, data={}, error_info="")

    async def get_events(
        self,
        *,
        after_sequence: int = 0,
        task_ids: set[str] | None = None,
    ) -> list[EngineEventRecord]:
        async with self._lock:
            return [
                event.model_copy(deep=True)
                for event in self._events
                if event.sequence > after_sequence and (task_ids is None or event.task_id in task_ids)
            ]

    async def aclose(self) -> None:
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            runners = [
                record.runner
                for record in self._tasks.values()
                if record.runner is not None and not record.runner.done()
            ]
            runners.extend(runner for runner in self._sim_runners if not runner.done())
            for runner in runners:
                runner.cancel()
            self._tasks.clear()
            self._events.clear()
            self._sim_runners.clear()

        if runners:
            await asyncio.gather(*runners, return_exceptions=True)

    async def _run_lifecycle(self, task_id: str) -> None:
        try:
            await self._set_state(task_id, EngineTaskState.PENDING)
            await asyncio.sleep(self._pending_seconds)
            await self._set_state(task_id, EngineTaskState.RUNNING)
            await self._append_agent_event(task_id)
            await self._run_and_emit_logs(task_id)
            await self._set_state(task_id, EngineTaskState.STOPPING)
            await asyncio.sleep(self._stopping_seconds)
            await self._set_state(task_id, EngineTaskState.END)
        except asyncio.CancelledError:
            raise

    async def _run_and_emit_logs(self, task_id: str) -> None:
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        deadline = started_at + self._task_duration_seconds

        while (remaining := deadline - loop.time()) > 0:
            await asyncio.sleep(min(self._log_interval_seconds, remaining))
            elapsed = min(self._task_duration_seconds, loop.time() - started_at)
            if self._task_duration_seconds == 0:
                progress = 100
            else:
                progress = round((elapsed / self._task_duration_seconds) * 100)
            await self._append_log(task_id, f"Task {task_id} progress {progress}%")

    async def _finish_stopping(self, task_id: str) -> None:
        try:
            await asyncio.sleep(self._stopping_seconds)
            await self._set_state(task_id, EngineTaskState.END)
        except asyncio.CancelledError:
            raise

    async def _set_state(self, task_id: str, state: EngineTaskState) -> None:
        async with self._lock:
            if self._closed:
                return
            record = self._tasks.get(task_id)
            if record is None or record.state is state:
                return
            record.state = state
            self._append_state_event_locked(record)

    async def _append_log(self, task_id: str, message: str) -> None:
        async with self._lock:
            if self._closed:
                return
            record = self._tasks.get(task_id)
            if record is None or record.state is not EngineTaskState.RUNNING or record.definition.is_box:
                return
            payload = EngineLogDispatchMessage(
                biz_value=record.definition.biz_value.model_copy(deep=True),
                level="info",
                message=message,
            )
            self._append_event_locked(task_id, payload)

    async def _append_agent_event(self, task_id: str) -> None:
        async with self._lock:
            if self._closed:
                return
            record = self._tasks.get(task_id)
            if record is None or record.state is not EngineTaskState.RUNNING or record.definition.is_box:
                return
            payload = EngineAgentEventDispatchMessage(
                biz_value=record.definition.biz_value.model_copy(deep=True),
                level="info",
                message=f"Task {task_id} emitted a runtime event",
            )
            self._append_event_locked(task_id, payload)

    async def _run_sim_time(
        self,
        task_ids: list[str],
        definition: EngineTaskDefinition,
        deduce_id: str | None,
    ) -> None:
        try:
            while True:
                await asyncio.sleep(self._sim_time_interval_seconds)
                async with self._lock:
                    if self._closed:
                        return
                    active = any(
                        (record := self._tasks.get(task_id)) is not None
                        and record.state not in {EngineTaskState.END, EngineTaskState.ERROR}
                        for task_id in task_ids
                    )
                    if not active:
                        return
                    self._append_sim_time_event_locked(definition, deduce_id)
        except asyncio.CancelledError:
            raise

    def _append_sim_time_event_locked(
        self,
        definition: EngineTaskDefinition,
        deduce_id: str | None,
    ) -> None:
        values = definition.env_config.env_instance_config
        payload = EngineSimTimeMessage(
            containerIp=values.get("ip") if isinstance(values.get("ip"), str) else None,
            containerPort=values.get("port") if isinstance(values.get("port"), int) else None,
            simTime=datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            healthOrNot=True,
        )
        self._events.append(
            EngineEventRecord(
                sequence=self._next_sequence,
                source="sim_time",
                deduce_id=deduce_id,
                task_id=None,
                payload=payload,
            )
        )
        self._next_sequence += 1

    def _append_state_event_locked(self, record: _FakeTaskRecord) -> None:
        payload = EngineStateDispatchMessage(
            biz_value=record.definition.biz_value.model_copy(deep=True),
            message=EngineStateChange(id=record.definition.id, now=record.state),
        )
        self._append_event_locked(record.definition.id, payload)

    def _append_event_locked(
        self,
        task_id: str,
        payload: (EngineStateDispatchMessage | EngineLogDispatchMessage | EngineAgentEventDispatchMessage),
    ) -> None:
        self._events.append(
            EngineEventRecord(
                sequence=self._next_sequence,
                deduce_id=payload.biz_value.deduce_id,
                task_id=task_id,
                payload=payload,
            )
        )
        self._next_sequence += 1
