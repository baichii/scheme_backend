import asyncio

import pytest
from sqlalchemy import select

from backend.app.deduction_run.model.deduction_run import DeductionRun
from backend.app.deduction_run.service.coordinator import DeductionRunCoordinator
from backend.engine.fake import FakeEngineClient


async def wait_for_status(client, run_id: str, expected: str, timeout: float = 1.0) -> dict:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        response = await client.get(f"/api/v2/deduction-runs/{run_id}")
        if response.json()["status"] == expected:
            return response.json()
        await asyncio.sleep(0.005)
    pytest.fail(f"Run {run_id} did not reach {expected}")


@pytest.mark.asyncio
async def test_full_fake_runtime_loop_and_matrix_compilation(runtime_client):
    client, session_factory, deduction_id, _ = runtime_client
    response = await client.post(
        "/api/v2/deduction-runs",
        json={"deductionId": str(deduction_id), "environmentResourceId": "6001"},
    )
    assert response.status_code == 200
    created = response.json()
    assert created["status"] == "starting"
    assert len([task for task in created["tasks"] if task["kind"] == "container"]) == 2
    assert len([task for task in created["tasks"] if task["kind"] == "agent"]) == 6

    async with session_factory() as db:
        run = (await db.execute(select(DeductionRun))).scalar_one()
        request = run.engine_request
    containers = [task for task in request["body"] if task["isBox"]]
    agents = [task for task in request["body"] if not task["isBox"]]
    assert containers[0]["isRoot"] is True
    assert containers[1]["pin"]["activate"] == f"{containers[0]['id']}:3"
    assert all(task["agentLoad"] == "runtime_agent" for task in agents)
    assert all(task["agentUrl"].startswith("http://test/api/v2/resources/10000/") for task in agents)
    assert all(task["father"] in {item["id"] for item in containers} for task in agents)
    assert all(task["bizValue"]["deduceID"] == created["id"] for task in request["body"])

    finished = await wait_for_status(client, created["id"], "finished")
    assert finished["sequence"] > 1
    assert all(task["status"] == "END" for task in finished["tasks"])
    events = await client.get(f"/api/v2/deduction-runs/{created['id']}/events")
    assert events.status_code == 200
    assert events.json()["items"]
    agent_task = next(task for task in finished["tasks"] if task["kind"] == "agent")
    logs = await client.get(
        f"/api/v2/deduction-runs/{created['id']}/logs", params={"taskId": agent_task["id"]}
    )
    assert logs.status_code == 200
    assert logs.json()["items"]
    assert all(item["taskId"] == agent_task["id"] for item in logs.json()["items"])
    container_task = next(task for task in finished["tasks"] if task["kind"] == "container")
    invalid_logs = await client.get(
        f"/api/v2/deduction-runs/{created['id']}/logs",
        params={"taskId": container_task["id"]},
    )
    assert invalid_logs.status_code == 422
    assert (await client.post(f"/api/v2/deduction-runs/{created['id']}/stop")).status_code == 409


@pytest.mark.asyncio
async def test_stop_latest_run_overlay_and_active_definition_lock(runtime_client):
    client, _, deduction_id, _ = runtime_client
    started = (
        await client.post(
            "/api/v2/deduction-runs",
            json={"deductionId": str(deduction_id), "environmentResourceId": "6001"},
        )
    ).json()
    locked = await client.put(f"/api/v2/deductions/{deduction_id}", json={"description": "不应成功"})
    assert locked.status_code == 409
    duplicate = await client.post(
        "/api/v2/deduction-runs",
        json={"deductionId": str(deduction_id), "environmentResourceId": "6001"},
    )
    assert duplicate.status_code == 409

    stopping = await client.post(f"/api/v2/deduction-runs/{started['id']}/stop")
    assert stopping.status_code == 200
    assert stopping.json()["status"] == "stopping"
    stopped = await wait_for_status(client, started["id"], "stopped")
    assert all(task["status"] == "END" for task in stopped["tasks"])
    repeat = await client.post(f"/api/v2/deduction-runs/{started['id']}/stop")
    assert repeat.status_code == 200
    assert repeat.json()["status"] == "stopped"

    detail = await client.get(f"/api/v2/deductions/{deduction_id}")
    assert detail.json()["latestRun"]["id"] == started["id"]
    page = await client.get("/api/v2/deductions", params={"runStatus": "stopped"})
    assert page.json()["total"] == 1


@pytest.mark.asyncio
async def test_runtime_message_replay_is_independent_for_multiple_viewers(runtime_client):
    client, _, deduction_id, coordinator = runtime_client
    started = (
        await client.post(
            "/api/v2/deduction-runs",
            json={"deductionId": str(deduction_id), "environmentResourceId": "6001"},
        )
    ).json()
    await wait_for_status(client, started["id"], "finished")
    first = coordinator.iter_messages(int(started["id"]), 0)
    second = coordinator.iter_messages(int(started["id"]), 0)
    first_message, second_message = await asyncio.gather(anext(first), anext(second))
    assert first_message == second_message
    assert first_message["sequence"] == 1
    await first.aclose()
    await second.aclose()


@pytest.mark.asyncio
async def test_backend_restart_marks_active_fake_run_failed(runtime_client):
    client, session_factory, deduction_id, coordinator = runtime_client
    started = (
        await client.post(
            "/api/v2/deduction-runs",
            json={"deductionId": str(deduction_id), "environmentResourceId": "6001"},
        )
    ).json()
    await coordinator.aclose()
    restarted = DeductionRunCoordinator(
        session_factory=session_factory,
        engine=FakeEngineClient(),
        poll_interval=0.001,
        heartbeat_seconds=0.02,
    )
    try:
        await restarted.reconcile()
        failed = await client.get(f"/api/v2/deduction-runs/{started['id']}")
        assert failed.json()["status"] == "failed"
        assert all(task["status"] == "ERROR" for task in failed.json()["tasks"])
    finally:
        await restarted.aclose()
