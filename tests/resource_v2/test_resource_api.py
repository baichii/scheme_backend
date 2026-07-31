import json

import pytest
from httpx import AsyncClient

from tests.resource_v2.conftest import MemoryObjectStorage
from tests.resource_v2.helpers import agent_file, scenario_file, strategy_file


def metadata(**values: object) -> dict[str, tuple[None, str]]:
    return {"metadata": (None, json.dumps(values, ensure_ascii=False))}


@pytest.mark.asyncio
async def test_creates_all_resource_types_and_lists_them(
    resource_client: tuple[AsyncClient, MemoryObjectStorage],
) -> None:
    client, _ = resource_client
    scenario = await client.post(
        "/api/v2/resources",
        files={
            **metadata(type="scenario", name="ignored", version="1.0"),
            "file": ("zc3.json", scenario_file()),
        },
    )
    strategy = await client.post(
        "/api/v2/resources",
        files={
            **metadata(type="strategy", name="测试策略", version="1.0"),
            "file": ("strategy.json", strategy_file()),
        },
    )
    agent = await client.post(
        "/api/v2/resources",
        files={**metadata(type="agent", name="版本测试智能体"), "file": ("agent.zip", agent_file())},
    )
    environment = await client.post(
        "/api/v2/resources",
        files=metadata(
            type="environment",
            name="本地联调环境",
            environment={
                "template": "local_test",
                "scenarioTypeKey": "zc3",
                "values": {"ip": "127.0.0.1", "port": 9500},
            },
        ),
    )

    assert [response.status_code for response in (scenario, strategy, agent, environment)] == [
        200,
        200,
        200,
        200,
    ]
    assert agent.json()["id"] == "10000"
    assert agent.json()["versions"][0]["version"] == "R1"
    page = (await client.get("/api/v2/resources", params={"type": "all", "pageSize": 100})).json()
    assert page["total"] == 4
    assert {item["type"] for item in page["items"]} == {"scenario", "strategy", "agent", "environment"}


@pytest.mark.asyncio
async def test_agent_replacement_archive_restore_and_duplicate_content(
    resource_client: tuple[AsyncClient, MemoryObjectStorage],
) -> None:
    client, _ = resource_client
    created = await client.post(
        "/api/v2/resources",
        files={**metadata(type="agent", name="版本智能体"), "file": ("agent.zip", agent_file())},
    )
    resource_id = created.json()["id"]
    replacement = await client.post(
        f"/api/v2/resources/{resource_id}/versions",
        files={"file": ("agent-2.zip", agent_file("2.0.0"))},
    )

    assert replacement.status_code == 200
    assert replacement.json()["version"]["version"] == "R2"
    third = await client.post(
        f"/api/v2/resources/{resource_id}/versions",
        files={"file": ("agent-3.zip", agent_file("2.0.0", extra="NOTE: patched\n"))},
    )
    assert third.status_code == 200
    assert third.json()["version"]["version"] == "R3"
    assert third.json()["packageVersionUnchanged"] is True
    duplicate = await client.post(
        f"/api/v2/resources/{resource_id}/versions",
        files={"file": ("agent-2.zip", agent_file("2.0.0"))},
    )
    assert duplicate.status_code == 409
    assert (await client.post(f"/api/v2/resources/{resource_id}/archive")).status_code == 204
    assert (await client.get("/api/v2/resources", params={"type": "agent"})).json()["total"] == 0
    assert (await client.post(f"/api/v2/resources/{resource_id}/restore")).status_code == 204


@pytest.mark.asyncio
async def test_download_and_fake_environment_runtime(
    resource_client: tuple[AsyncClient, MemoryObjectStorage],
) -> None:
    client, _ = resource_client
    created = await client.post(
        "/api/v2/resources",
        files={
            **metadata(type="scenario", name="ignored", version="1.0"),
            "file": ("zc3.json", scenario_file()),
        },
    )
    version = created.json()["versions"][0]
    download = await client.get(version["downloadUrl"])
    assert download.content == scenario_file()
    assert "attachment" in download.headers["content-disposition"]

    environment = await client.post(
        "/api/v2/resources",
        files=metadata(
            type="environment",
            name="断开环境",
            environment={
                "template": "local_test",
                "scenarioTypeKey": "local_test",
                "values": {"ip": "127.0.0.1", "port": 9501},
            },
        ),
    )
    runtime = await client.get(f"/api/v2/resources/{environment.json()['id']}/runtime")
    assert runtime.json() == {"status": "disconnected"}


@pytest.mark.asyncio
async def test_rejects_duplicate_names_and_invalid_environment(
    resource_client: tuple[AsyncClient, MemoryObjectStorage],
) -> None:
    client, storage = resource_client
    first = await client.post(
        "/api/v2/resources",
        files={**metadata(type="agent", name="同名智能体"), "file": ("agent.zip", agent_file())},
    )
    duplicate = await client.post(
        "/api/v2/resources",
        files={**metadata(type="agent", name="同名智能体"), "file": ("other.zip", agent_file("1.1.0"))},
    )
    invalid = await client.post(
        "/api/v2/resources",
        files=metadata(
            type="environment",
            name="错误环境",
            environment={"template": "missing", "scenarioTypeKey": "zc3", "values": {}},
        ),
    )

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert invalid.status_code == 422
    assert len(storage.deleted) == 1
    assert len(storage.objects) == 1


@pytest.mark.asyncio
async def test_storage_upload_failure_does_not_create_resource(
    resource_client: tuple[AsyncClient, MemoryObjectStorage],
) -> None:
    client, storage = resource_client

    class FailingStorage(MemoryObjectStorage):
        async def put(self, object_name: str, data: bytes, content_type: str) -> None:
            raise RuntimeError("storage unavailable")

    from backend.app.resource.service.resource_service import resource_service

    resource_service.storage = FailingStorage()
    try:
        with pytest.raises(RuntimeError, match="storage unavailable"):
            await client.post(
                "/api/v2/resources",
                files={
                    **metadata(type="agent", name="上传失败智能体"),
                    "file": ("agent.zip", agent_file()),
                },
            )
    finally:
        resource_service.storage = storage
    assert (await client.get("/api/v2/resources", params={"type": "agent"})).json()["total"] == 0
