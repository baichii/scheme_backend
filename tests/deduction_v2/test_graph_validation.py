from copy import deepcopy

import pytest
from httpx import AsyncClient

from tests.deduction_v2.helpers import branch, ready_graph


def remove_end(graph: dict) -> None:
    graph["nodes"] = [node for node in graph["nodes"] if node["kind"] != "end"]


def duplicate_edge_id(graph: dict) -> None:
    graph["edges"].extend(
        [
            {"id": "edge", "source": "start", "target": "branch-1"},
            {"id": "edge", "source": "branch-1", "target": "end"},
        ]
    )


def duplicate_connection(graph: dict) -> None:
    graph["edges"].extend(
        [
            {"id": "edge-1", "source": "start", "target": "branch-1"},
            {"id": "edge-2", "source": "start", "target": "branch-1"},
        ]
    )


def duplicate_branch_scheme(graph: dict) -> None:
    graph["nodes"].append(branch("branch-2", "scheme-1"))


async def create(client: AsyncClient) -> dict:
    response = await client.post("/api/v2/deductions", json={"name": "图校验", "scenarioTypeKey": "zc"})
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda graph: graph["nodes"].append(deepcopy(graph["nodes"][0])),
        lambda graph: graph["edges"].append({"id": "missing", "source": "start", "target": "not-found"}),
        lambda graph: graph["edges"].append({"id": "reverse", "source": "end", "target": "start"}),
        lambda graph: graph["edges"].append(
            {
                "id": "handle",
                "source": "start",
                "target": "branch-1",
                "sourceHandle": "top-out",
            }
        ),
        lambda graph: graph["edges"].append(
            {
                "id": "handle",
                "source": "branch-1",
                "target": "end",
                "targetHandle": "top-in",
            }
        ),
        duplicate_edge_id,
        duplicate_connection,
        duplicate_branch_scheme,
        remove_end,
    ],
    ids=[
        "duplicate-node",
        "missing-node",
        "bad-direction",
        "bad-start-handle",
        "bad-end-handle",
        "duplicate-edge-id",
        "duplicate-connection",
        "duplicate-branch-scheme",
        "missing-end",
    ],
)
async def test_invalid_graph_returns_422(client: AsyncClient, mutate) -> None:
    created = await create(client)
    graph = created["graph"]
    if not any(node["kind"] == "branch-scheme" for node in graph["nodes"]):
        graph["nodes"].append(branch("branch-1", "scheme-1"))
    mutate(graph)

    response = await client.put(f"/api/v2/deductions/{created['id']}", json={"graph": graph})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ready_requires_minimum_branches_and_full_connectivity(client: AsyncClient) -> None:
    created = await create(client)
    minimum = await client.put(f"/api/v2/deductions/{created['id']}", json={"status": "ready"})
    assert minimum.status_code == 422

    disconnected = ready_graph()
    disconnected["edges"] = disconnected["edges"][:1]
    response = await client.put(
        f"/api/v2/deductions/{created['id']}",
        json={"graph": disconnected, "status": "ready"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_request_validation_returns_422(client: AsyncClient) -> None:
    invalid_payloads = [
        {"name": " ", "scenarioTypeKey": "zc"},
        {"name": "x" * 81, "scenarioTypeKey": "zc"},
        {"name": "Valid", "scenarioTypeKey": " "},
    ]
    for payload in invalid_payloads:
        response = await client.post("/api/v2/deductions", json=payload)
        assert response.status_code == 422
