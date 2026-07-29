import asyncio

import pytest

from backend.engine.fake import FakeEngineClient
from backend.engine.schemas import (
    EngineCreateRequest,
    EngineQueryRequest,
    EngineStateDispatchMessage,
    EngineStopRequest,
    EngineTaskDefinition,
    EngineTaskState,
)


def make_client(*, stopping_seconds: float = 0.01) -> FakeEngineClient:
    return FakeEngineClient(
        pending_seconds=0.01,
        task_duration_seconds=0.04,
        stopping_seconds=stopping_seconds,
        log_interval_seconds=0.005,
    )


def make_task(task_id: str, **values) -> EngineTaskDefinition:
    return EngineTaskDefinition(
        id=task_id,
        bizValue={
            "dispatchQueue": {"name": "scheme"},
            "deduceID": "deduction-1",
            "deduceTaskID": task_id,
        },
        **values,
    )


async def wait_for_state(
    client: FakeEngineClient,
    task_id: str,
    expected: EngineTaskState,
    *,
    timeout: float = 0.5,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        response = await client.query(EngineQueryRequest(body=[task_id]))
        if response.data[task_id] is expected:
            return
        await asyncio.sleep(0.001)
    pytest.fail(f"Task {task_id} did not reach {expected.value}")


@pytest.mark.asyncio
async def test_full_lifecycle_emits_matrix_state_and_log_messages():
    client = make_client()
    try:
        response = await client.create(EngineCreateRequest(body=[make_task("task-1")]))
        assert response.model_dump(mode="json") == {"code": 200, "data": "", "error_info": ""}

        await wait_for_state(client, "task-1", EngineTaskState.END)
        events = await client.get_events()
        state_events = [event for event in events if isinstance(event.payload, EngineStateDispatchMessage)]

        assert [event.payload.message.now for event in state_events] == [
            EngineTaskState.READY,
            EngineTaskState.PENDING,
            EngineTaskState.RUNNING,
            EngineTaskState.STOPPING,
            EngineTaskState.END,
        ]
        assert any(event.payload.message_type == "log" for event in events)
        assert [event.sequence for event in events] == list(range(1, len(events) + 1))
        assert state_events[0].payload.model_dump(mode="json", by_alias=True) == {
            "messageType": "state",
            "bizValue": {
                "dispatchQueue": {"name": "scheme", "durable": True, "needToDeclare": True},
                "simTimeQueue": {"name": "", "durable": True, "needToDeclare": True},
                "deduceID": "deduction-1",
                "deduceTaskID": "task-1",
            },
            "message": {"id": "task-1", "now": "0"},
        }
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_tasks_run_in_parallel_without_interpreting_pin_or_father():
    client = make_client()
    try:
        request = EngineCreateRequest(
            body=[
                make_task("task-1"),
                make_task("task-2", father="task-1", pin={"activate": "task-1:4"}),
            ]
        )
        assert (await client.create(request)).code == 200

        await wait_for_state(client, "task-1", EngineTaskState.RUNNING)
        response = await client.query(EngineQueryRequest(body=["task-1", "task-2", "unknown"]))
        assert response.data == {
            "task-1": EngineTaskState.RUNNING,
            "task-2": EngineTaskState.RUNNING,
            "unknown": EngineTaskState.UNKNOWN,
        }
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_duplicate_ids_fail_atomically():
    client = make_client()
    try:
        duplicate = EngineCreateRequest(body=[make_task("task-1"), make_task("task-1")])
        response = await client.create(duplicate)
        assert response.code == 400
        assert (await client.query(EngineQueryRequest(body=["task-1"]))).data == {
            "task-1": EngineTaskState.UNKNOWN
        }

        assert (await client.create(EngineCreateRequest(body=[make_task("task-1")]))).code == 200
        existing = await client.create(EngineCreateRequest(body=[make_task("task-1"), make_task("task-2")]))
        assert existing.code == 400
        assert (await client.query(EngineQueryRequest(body=["task-2"]))).data == {
            "task-2": EngineTaskState.UNKNOWN
        }
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_stop_is_idempotent_and_uses_stopping_before_end():
    client = make_client(stopping_seconds=0.03)
    try:
        await client.create(EngineCreateRequest(body=[make_task("task-1")]))
        await wait_for_state(client, "task-1", EngineTaskState.RUNNING)

        response = await client.stop(EngineStopRequest(body=["task-1", "unknown"]))
        assert response.model_dump(mode="json") == {"code": 200, "data": {}, "error_info": ""}
        assert (await client.query(EngineQueryRequest(body=["task-1"]))).data[
            "task-1"
        ] is EngineTaskState.STOPPING

        events_before_repeat = await client.get_events()
        await client.stop(EngineStopRequest(body=["task-1", "unknown"]))
        assert len(await client.get_events()) == len(events_before_repeat)

        await wait_for_state(client, "task-1", EngineTaskState.END)
        events_at_end = await client.get_events()
        await client.stop(EngineStopRequest(body=["task-1"]))
        assert len(await client.get_events()) == len(events_at_end)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_stop_during_startup_cancels_the_normal_lifecycle():
    client = FakeEngineClient(
        pending_seconds=0.1,
        task_duration_seconds=0.1,
        stopping_seconds=0.01,
        log_interval_seconds=0.01,
    )
    try:
        await client.create(EngineCreateRequest(body=[make_task("task-1")]))
        await client.stop(EngineStopRequest(body=["task-1"]))
        await wait_for_state(client, "task-1", EngineTaskState.END)

        state_events = [
            event.payload.message.now
            for event in await client.get_events()
            if isinstance(event.payload, EngineStateDispatchMessage)
        ]
        assert state_events[-2:] == [EngineTaskState.STOPPING, EngineTaskState.END]
        assert EngineTaskState.RUNNING not in state_events
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_events_support_cursor_filtering_and_return_deep_copies():
    client = make_client()
    try:
        await client.create(EngineCreateRequest(body=[make_task("task-1"), make_task("task-2")]))
        await wait_for_state(client, "task-1", EngineTaskState.RUNNING)

        all_events = await client.get_events()
        cursor = all_events[1].sequence
        filtered = await client.get_events(after_sequence=cursor, task_ids={"task-2"})
        assert filtered
        assert all(event.sequence > cursor and event.task_id == "task-2" for event in filtered)

        original_task_id = filtered[0].task_id
        filtered[0].task_id = "mutated"
        reread = await client.get_events(after_sequence=cursor, task_ids={"task-2"})
        assert reread[0].task_id == original_task_id
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_aclose_cancels_lifecycle_and_clears_memory():
    client = make_client()
    await client.create(EngineCreateRequest(body=[make_task("task-1")]))
    await wait_for_state(client, "task-1", EngineTaskState.PENDING)

    await client.aclose()
    await asyncio.sleep(0.02)

    assert await client.get_events() == []
    assert (await client.query(EngineQueryRequest(body=["task-1"]))).data == {
        "task-1": EngineTaskState.UNKNOWN
    }
    assert (await client.create(EngineCreateRequest(body=[make_task("task-2")]))).code == 400
