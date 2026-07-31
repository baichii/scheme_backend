import asyncio

import pytest
from httpx import AsyncClient

from tests.deduction_v2.helpers import ready_graph


async def create(client: AsyncClient, name: str, description: str = "") -> dict:
    response = await client.post(
        "/api/v2/deductions",
        json={"name": name, "description": description, "scenarioTypeKey": "zc"},
    )
    assert response.status_code == 200
    await asyncio.sleep(0.002)
    return response.json()


@pytest.mark.asyncio
async def test_list_search_sort_pagination_and_branch_count(client: AsyncClient) -> None:
    await create(client, "Alpha", "海上任务")
    beta = await create(client, "Beta", "空中任务")
    await create(client, "Gamma", "海上支援")
    ready = await client.put(
        f"/api/v2/deductions/{beta['id']}", json={"graph": ready_graph(), "status": "ready"}
    )
    assert ready.status_code == 200

    page = await client.get("/api/v2/deductions", params={"page": 1, "pageSize": 2, "sortOrder": "asc"})
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert page.json()["pageSize"] == 2
    assert [item["name"] for item in page.json()["items"]] == ["Alpha", "Gamma"]

    search = await client.get("/api/v2/deductions", params={"search": "海上", "pageSize": 10})
    assert {item["name"] for item in search.json()["items"]} == {"Alpha", "Gamma"}

    filtered = await client.get("/api/v2/deductions", params={"status": "ready"})
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["branchSchemeCount"] == 2


@pytest.mark.asyncio
async def test_runtime_status_filter_is_empty(client: AsyncClient) -> None:
    await create(client, "Alpha")
    for runtime_status in ("starting", "running", "stopping", "finished", "failed", "stopped"):
        response = await client.get("/api/v2/deductions", params={"runStatus": runtime_status})
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0
