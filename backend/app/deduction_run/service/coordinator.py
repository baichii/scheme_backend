import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.deduction_run.crud.deduction_run import (
    deduction_run_dao,
    deduction_runtime_message_dao,
    deduction_task_dao,
)
from backend.app.deduction_run.schema.deduction_run import (
    RuntimeEventMessage,
    RuntimeLogMessage,
    RuntimeRunStateMessage,
    RuntimeSimTimeMessage,
    RuntimeTaskStateMessage,
)
from backend.database.db import async_db_session
from backend.engine import EngineClient, get_engine_client
from backend.engine.schemas import (
    EngineAgentEventDispatchMessage,
    EngineCreateRequest,
    EngineEventRecord,
    EngineLogDispatchMessage,
    EngineQueryRequest,
    EngineSimTimeMessage,
    EngineStateDispatchMessage,
    EngineStopRequest,
    EngineTaskState,
)
from backend.utils.timezone import timezone

TERMINAL_RUN_STATUSES = {"finished", "failed", "stopped"}
TERMINAL_TASK_STATUSES = {"END", "ERROR"}


class RuntimeSignal:
    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._versions: dict[int, int] = {}

    def version(self, run_id: int) -> int:
        return self._versions.get(run_id, 0)

    async def notify(self, run_id: int) -> None:
        async with self._condition:
            self._versions[run_id] = self.version(run_id) + 1
            self._condition.notify_all()

    async def wait(self, run_id: int, version: int, timeout: float) -> bool:
        async with self._condition:
            if self.version(run_id) != version:
                return True
            try:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: self.version(run_id) != version),
                    timeout=timeout,
                )
            except TimeoutError:
                return False
            return True


class DeductionRunCoordinator:
    """连接持久化 Runtime 与 Engine Client 的进程内协调器。"""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        engine: EngineClient,
        poll_interval: float,
        heartbeat_seconds: float,
    ) -> None:
        self.session_factory = session_factory
        self.engine = engine
        self.poll_interval = poll_interval
        self.heartbeat_seconds = heartbeat_seconds
        self.signal = RuntimeSignal()
        self._runners: dict[int, asyncio.Task[None]] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._closed = False

    async def notify(self, run_id: int) -> None:
        await self.signal.notify(run_id)

    async def start_run(self, run_id: int) -> None:
        lock = self._locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            async with self.session_factory() as db:
                run = await deduction_run_dao.get(db, run_id)
                if not run or run.status in TERMINAL_RUN_STATUSES:
                    return
                if run.status == "stopping":
                    await self._finish_without_engine(run_id)
                    return
                request = EngineCreateRequest.model_validate(run.engine_request)
            response = await self.engine.create(request)
            if response.code != 200:
                await self.fail_run(run_id, response.error_info or "Engine create failed")
                return
            await self._set_run_status(run_id, "running")
            self._ensure_pump(run_id)

    async def stop_run(self, run_id: int) -> None:
        await self.notify(run_id)
        lock = self._locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            async with self.session_factory() as db:
                run = await deduction_run_dao.get(db, run_id)
                if not run or run.status == "stopped":
                    return
                tasks = await deduction_task_dao.get_by_run(db, run_id)
                unfinished = [str(task.id) for task in tasks if task.status not in TERMINAL_TASK_STATUSES]
            if not unfinished:
                await self._set_run_status(run_id, "stopped")
                return
            response = await self.engine.stop(EngineStopRequest(body=unfinished))
            if response.code != 200:
                await self.fail_run(run_id, response.error_info or "Engine stop failed")
                return
            query = await self.engine.query(EngineQueryRequest(body=unfinished))
            if all(state is EngineTaskState.UNKNOWN for state in query.data.values()):
                await self._finish_without_engine(run_id)
                return
            self._ensure_pump(run_id)

    def _ensure_pump(self, run_id: int) -> None:
        current = self._runners.get(run_id)
        if current and not current.done():
            return
        runner = asyncio.create_task(self._pump(run_id), name=f"deduction-run-{run_id}")
        self._runners[run_id] = runner
        runner.add_done_callback(lambda _: self._runners.pop(run_id, None))

    async def _pump(self, run_id: int) -> None:
        try:
            while not self._closed:
                async with self.session_factory() as db:
                    run = await deduction_run_dao.get(db, run_id)
                    if not run or run.status in TERMINAL_RUN_STATUSES:
                        return
                    cursor = run.engine_cursor
                records = await self.engine.get_events(after_sequence=cursor)
                if not records:
                    await asyncio.sleep(self.poll_interval)
                    continue
                for record in records:
                    await self._process_record(run_id, record)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.fail_run(run_id, f"Engine event pump failed: {exc}")

    async def _process_record(self, run_id: int, record: EngineEventRecord) -> None:
        should_evaluate = False
        emitted = False
        async with self.session_factory.begin() as db:
            run = await deduction_run_dao.get(db, run_id, for_update=True)
            if not run or record.sequence <= run.engine_cursor:
                return
            run.engine_cursor = record.sequence
            if record.deduce_id != str(run_id):
                return
            now = timezone.now()
            payload = record.payload
            if isinstance(payload, EngineStateDispatchMessage) and record.task_id:
                task = await deduction_task_dao.get(db, int(record.task_id))
                if task and task.run_id == run_id and task.status != payload.message.now.name:
                    status = payload.message.now.name
                    task.status = status
                    if status == "RUNNING" and not task.started_at:
                        task.started_at = now
                    if status in TERMINAL_TASK_STATUSES and not task.ended_at:
                        task.ended_at = now
                    message = RuntimeTaskStateMessage(
                        sequence=run.sequence + 1,
                        runId=str(run.id),
                        emittedAt=now,
                        simTime=run.sim_time,
                        taskId=str(task.id),
                        status=status,
                        startedAt=task.started_at,
                        endedAt=task.ended_at,
                    )
                    await self._store_message(db, run, message, task=task)
                    should_evaluate = True
                    emitted = True
            elif isinstance(payload, EngineSimTimeMessage):
                run.sim_time = payload.sim_time
                run.environment_runtime = {
                    "status": "healthy" if payload.health_or_not else "unhealthy",
                    "checkedAt": now.isoformat(),
                    "containerIp": payload.container_ip,
                    "containerPort": payload.container_port,
                }
                message = RuntimeSimTimeMessage(
                    sequence=run.sequence + 1,
                    runId=str(run.id),
                    emittedAt=now,
                    simTime=payload.sim_time,
                    healthOrNot=payload.health_or_not,
                    containerIp=payload.container_ip,
                    containerPort=payload.container_port,
                )
                await self._store_message(db, run, message)
                emitted = True
            elif isinstance(payload, (EngineLogDispatchMessage, EngineAgentEventDispatchMessage)):
                if record.task_id:
                    task = await deduction_task_dao.get(db, int(record.task_id))
                    if task and task.run_id == run_id and task.kind == "agent":
                        level = self._normalize_level(payload.level)
                        common = {
                            "sequence": run.sequence + 1,
                            "runId": str(run.id),
                            "emittedAt": now,
                            "simTime": run.sim_time,
                            "level": level,
                            "content": payload.message,
                            "taskId": str(task.id),
                            "taskName": task.name,
                            "branchNodeId": task.branch_node_id,
                            "branchSchemeId": str(task.branch_scheme_id),
                            "branchSchemeName": task.branch_scheme_name,
                        }
                        message = (
                            RuntimeEventMessage(**common, title=task.name)
                            if isinstance(payload, EngineAgentEventDispatchMessage)
                            else RuntimeLogMessage(**common)
                        )
                        await self._store_message(db, run, message, task=task)
                        emitted = True
        if emitted:
            await self.notify(run_id)
        if should_evaluate:
            await self._evaluate_run(run_id)

    @staticmethod
    def _normalize_level(level: str) -> str:
        if level == "debug":
            return "info"
        if level == "critical":
            return "error"
        return level

    async def _store_message(
        self,
        db: AsyncSession,
        run,
        message,
        *,
        task=None,
    ) -> None:
        run.sequence = message.sequence
        values: dict[str, Any] = {
            "run_id": run.id,
            "sequence": message.sequence,
            "type": message.type,
            "payload": message.model_dump(mode="json", by_alias=True, exclude_none=True),
            "emitted_at": message.emitted_at,
        }
        if task:
            values.update(task_id=task.id, branch_node_id=task.branch_node_id)
        await deduction_runtime_message_dao.create(db, values)

    async def _evaluate_run(self, run_id: int) -> None:
        async with self.session_factory() as db:
            run = await deduction_run_dao.get(db, run_id)
            if not run or run.status in TERMINAL_RUN_STATUSES:
                return
            tasks = await deduction_task_dao.get_by_run(db, run_id)
            if any(task.status == "ERROR" for task in tasks):
                await self.fail_run(run_id, "Engine task failed")
            elif tasks and all(task.status == "END" for task in tasks):
                await self._set_run_status(run_id, "stopped" if run.status == "stopping" else "finished")

    async def _set_run_status(self, run_id: int, status: str) -> None:
        emitted = False
        async with self.session_factory.begin() as db:
            run = await deduction_run_dao.get(db, run_id, for_update=True)
            if not run or run.status == status:
                return
            now = timezone.now()
            ended_at = now if status in TERMINAL_RUN_STATUSES else None
            run.status = status
            run.ended_at = ended_at
            message = RuntimeRunStateMessage(
                sequence=run.sequence + 1,
                runId=str(run.id),
                emittedAt=now,
                simTime=run.sim_time,
                status=status,
                endedAt=ended_at,
            )
            await self._store_message(db, run, message)
            emitted = True
        if emitted:
            await self.notify(run_id)

    async def _finish_without_engine(self, run_id: int) -> None:
        async with self.session_factory.begin() as db:
            run = await deduction_run_dao.get(db, run_id, for_update=True)
            if not run or run.status in TERMINAL_RUN_STATUSES:
                return
            tasks = await deduction_task_dao.get_by_run(db, run_id)
            now = timezone.now()
            for task in tasks:
                if task.status in TERMINAL_TASK_STATUSES:
                    continue
                task.status = "END"
                task.ended_at = now
                message = RuntimeTaskStateMessage(
                    sequence=run.sequence + 1,
                    runId=str(run.id),
                    emittedAt=now,
                    simTime=run.sim_time,
                    taskId=str(task.id),
                    status="END",
                    endedAt=now,
                )
                await self._store_message(db, run, message, task=task)
        await self.notify(run_id)
        await self._set_run_status(run_id, "stopped")

    async def fail_run(self, run_id: int, reason: str) -> None:
        async with self.session_factory.begin() as db:
            run = await deduction_run_dao.get(db, run_id, for_update=True)
            if not run or run.status in TERMINAL_RUN_STATUSES:
                return
            now = timezone.now()
            tasks = await deduction_task_dao.get_by_run(db, run_id)
            unfinished_ids: list[str] = []
            for task in tasks:
                if task.status in TERMINAL_TASK_STATUSES:
                    continue
                unfinished_ids.append(str(task.id))
                task.status = "ERROR"
                task.ended_at = now
                message = RuntimeTaskStateMessage(
                    sequence=run.sequence + 1,
                    runId=str(run.id),
                    emittedAt=now,
                    simTime=run.sim_time,
                    taskId=str(task.id),
                    status="ERROR",
                    endedAt=now,
                )
                await self._store_message(db, run, message, task=task)
            run.status = "failed"
            run.failure_reason = reason[:500]
            run.ended_at = now
            message = RuntimeRunStateMessage(
                sequence=run.sequence + 1,
                runId=str(run.id),
                emittedAt=now,
                simTime=run.sim_time,
                status="failed",
                endedAt=now,
            )
            await self._store_message(db, run, message)
        await self.notify(run_id)
        if unfinished_ids:
            with suppress(Exception):
                await self.engine.stop(EngineStopRequest(body=unfinished_ids))

    async def reconcile(self) -> None:
        async with self.session_factory() as db:
            active = await deduction_run_dao.get_active(db)
        for run in active:
            await self.fail_run(run.id, "Fake Engine context was lost during Backend restart")

    async def iter_messages(self, run_id: int, after_sequence: int) -> AsyncIterator[dict | None]:
        cursor = after_sequence
        while not self._closed:
            version = self.signal.version(run_id)
            async with self.session_factory() as db:
                rows = await deduction_runtime_message_dao.get_after(db, run_id=run_id, sequence=cursor)
            if rows:
                for row in rows:
                    cursor = row.sequence
                    yield dict(row.payload)
                continue
            changed = await self.signal.wait(run_id, version, self.heartbeat_seconds)
            if not changed:
                yield None

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        runners = [runner for runner in self._runners.values() if not runner.done()]
        for runner in runners:
            runner.cancel()
        if runners:
            await asyncio.gather(*runners, return_exceptions=True)
        self._runners.clear()
        await self.engine.aclose()


def create_deduction_run_coordinator(
    *,
    session_factory: async_sessionmaker[AsyncSession] = async_db_session,
    engine: EngineClient | None = None,
) -> DeductionRunCoordinator:
    from backend.core.conf import settings

    return DeductionRunCoordinator(
        session_factory=session_factory,
        engine=engine or get_engine_client(),
        poll_interval=settings.ENGINE_EVENT_POLL_INTERVAL_SECONDS,
        heartbeat_seconds=settings.RUNTIME_SSE_HEARTBEAT_SECONDS,
    )
