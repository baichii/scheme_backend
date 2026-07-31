import pytest
from httpx import AsyncClient
from sqlalchemy import BigInteger

from backend.app.deduction.model.deduction import Deduction
from tests.deduction_v2.helpers import branch, ready_graph


async def create(client: AsyncClient, name: str = "联合推演", description: str = "") -> dict:
    response = await client.post(
        "/api/v2/deductions",
        json={"name": name, "description": description, "scenarioTypeKey": "zc"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_get_and_delete(client: AsyncClient) -> None:
    created = await create(client, "  联合推演  ", "  测试描述  ")

    assert created["id"].isdigit()
    assert int(created["id"]) > 0
    assert created["name"] == "联合推演"
    assert created["description"] == "测试描述"
    assert created["scenarioTypeKey"] == "zc"
    assert created["status"] == "draft"
    assert created["createdBy"] == "当前用户"
    assert created["createdAt"]
    assert created["updatedAt"] == created["createdAt"]
    assert [node["kind"] for node in created["graph"]["nodes"]] == ["start", "end"]
    assert "viewport" not in created["graph"]
    assert "environmentResourceId" not in created
    assert "environmentName" not in created
    assert "latestRun" not in created

    fetched = await client.get(f"/api/v2/deductions/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created

    deleted = await client.delete(f"/api/v2/deductions/{created['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (await client.get(f"/api/v2/deductions/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_partial_update_and_ready_round_trip(client: AsyncClient) -> None:
    created = await create(client)
    response = await client.put(
        f"/api/v2/deductions/{created['id']}",
        json={"description": "新版描述", "graph": ready_graph(), "status": "ready"},
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == created["name"]
    assert updated["description"] == "新版描述"
    assert updated["status"] == "ready"
    assert updated["graph"]["viewport"] == {"x": 0.0, "y": 0.0, "zoom": 1.0}

    description_only = await client.put(
        f"/api/v2/deductions/{created['id']}", json={"description": "仍然有效"}
    )
    assert description_only.status_code == 200
    assert description_only.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_draft_accepts_disconnected_graph(client: AsyncClient) -> None:
    created = await create(client)
    graph = created["graph"]
    graph["nodes"].append(branch("branch-1", "101"))

    response = await client.put(f"/api/v2/deductions/{created['id']}", json={"graph": graph})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_casefold_name_conflicts_on_create_and_update(client: AsyncClient) -> None:
    first = await create(client, "Alpha")
    duplicate = await client.post("/api/v2/deductions", json={"name": "alpha", "scenarioTypeKey": "zc"})
    assert duplicate.status_code == 409

    second = await create(client, "Beta")
    conflict = await client.put(f"/api/v2/deductions/{second['id']}", json={"name": "ALPHA"})
    assert conflict.status_code == 409
    assert (await client.get(f"/api/v2/deductions/{first['id']}")).status_code == 200


@pytest.mark.asyncio
async def test_unknown_resources_and_deferred_runtime_routes(client: AsyncClient) -> None:
    missing = "/api/v2/deductions/999999999999999999"
    assert (await client.get(missing)).status_code == 404
    assert (await client.put(missing, json={"description": "x"})).status_code == 404
    assert (await client.delete(missing)).status_code == 404

    created = await create(client)
    for suffix, method in (("start", "post"), ("stop", "post"), ("runtime", "get")):
        response = await getattr(client, method)(f"/api/v2/deductions/{created['id']}/{suffix}")
        assert response.status_code in {404, 405}

    immutable_scenario = await client.put(
        f"/api/v2/deductions/{created['id']}", json={"scenarioTypeKey": "other"}
    )
    assert immutable_scenario.status_code == 422


@pytest.mark.asyncio
async def test_rejects_non_decimal_wire_ids(client: AsyncClient) -> None:
    for deduction_id in ("deduction-1", "-1", "0", "1.5"):
        response = await client.get(f"/api/v2/deductions/{deduction_id}")
        assert response.status_code == 422


def test_deduction_uses_bigint_snowflake_primary_key() -> None:
    column = Deduction.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, BigInteger)
    assert column.default is not None
