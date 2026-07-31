import pytest
from httpx import AsyncClient

from tests.branch_scheme_v2.helpers import (
    bind_default_graph,
    configure_branch,
    create_agent,
    create_branch,
)
from tests.resource_v2.helpers import agent_file


@pytest.mark.asyncio
async def test_revision_lifecycle_and_compare_and_swap(client: AsyncClient) -> None:
    branch = await create_branch(client)
    assert branch["status"] == "draft"
    assert branch["headRevisionNumber"] == 1
    assert "publishedRevisionId" not in branch

    agent = await create_agent(client)
    configured = await configure_branch(client, branch, agent)
    detail = (await client.get(f"/api/v2/branch-schemes/{branch['id']}")).json()
    assert configured["revisionNumber"] == 2
    assert detail["publishedRevisionId"] == configured["id"]
    assert detail["publishedRevisionNumber"] == 2

    draft = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={"baseRevisionId": configured["id"], "status": "draft", "description": "下一版草稿"},
    )
    assert draft.status_code == 200
    page = (await client.get("/api/v2/branch-schemes", params={"status": "configured"})).json()
    assert page["items"][0]["status"] == "configured"
    assert page["items"][0]["hasDraft"] is True
    assert page["items"][0]["description"] == "阶段 3 测试"

    stale = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={"baseRevisionId": configured["id"], "description": "冲突写入"},
    )
    assert stale.status_code == 409
    revisions = (await client.get(f"/api/v2/branch-schemes/{branch['id']}/revisions")).json()
    assert [revision["revisionNumber"] for revision in revisions] == [3, 2, 1]


@pytest.mark.asyncio
async def test_configured_binding_validation_and_archived_history(client: AsyncClient) -> None:
    branch = await create_branch(client)
    missing = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={"baseRevisionId": branch["headRevisionId"], "status": "configured"},
    )
    assert missing.status_code == 422

    agent = await create_agent(client)
    graph = bind_default_graph(branch, agent)
    graph["nodes"][1]["agentBinding"]["agentRevisionNumber"] = 99
    mismatch = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={"baseRevisionId": branch["headRevisionId"], "status": "configured", "graph": graph},
    )
    assert mismatch.status_code == 422

    configured = await configure_branch(client, branch, agent)
    assert (await client.post(f"/api/v2/resources/{agent['id']}/archive")).status_code == 204
    historical = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={"baseRevisionId": configured["id"], "description": "归档后保留旧绑定"},
    )
    assert historical.status_code == 200

    new_branch = await create_branch(client, "归档绑定测试")
    rejected = await client.post(
        f"/api/v2/branch-schemes/{new_branch['id']}/revisions",
        json={
            "baseRevisionId": new_branch["headRevisionId"],
            "status": "configured",
            "graph": bind_default_graph(new_branch, agent),
        },
    )
    assert rejected.status_code == 422


@pytest.mark.asyncio
async def test_configured_binding_requires_exact_valid_parameters(client: AsyncClient) -> None:
    agent = await create_agent(
        client,
        "带参数智能体",
        agent_file(
            params=[
                {
                    "name": "retry_limit",
                    "chineseName": "重试次数",
                    "type": "int",
                    "chineseType": "整数",
                    "description": "最大重试次数",
                    "required": True,
                    "defaultValue": 1,
                }
            ]
        ),
    )
    branch = await create_branch(client, "参数校验方案")
    graph = bind_default_graph(branch, agent)
    missing = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={
            "baseRevisionId": branch["headRevisionId"],
            "status": "configured",
            "graph": graph,
        },
    )
    assert missing.status_code == 422

    for node in graph["nodes"]:
        if node.get("agentBinding"):
            node["agentBinding"]["parameters"] = {"retry_limit": 2}
    configured = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={
            "baseRevisionId": branch["headRevisionId"],
            "status": "configured",
            "graph": graph,
        },
    )
    assert configured.status_code == 200, configured.text


@pytest.mark.asyncio
async def test_agent_impact_and_fixed_deduction_references(client: AsyncClient) -> None:
    agent = await create_agent(client)
    first = await create_branch(client, "红方主方案")
    second = await create_branch(client, "红方备选方案")
    first_revision = await configure_branch(client, first, agent)
    second_revision = await configure_branch(client, second, agent)

    replacement = await client.post(
        f"/api/v2/resources/{agent['id']}/versions",
        files={"file": ("agent-r2.zip", agent_file(extra="NOTE: changed\n"))},
    )
    assert replacement.status_code == 200, replacement.text
    assert replacement.json()["packageVersionUnchanged"] is True
    impacts = replacement.json()["impact"]["references"]
    assert len(impacts) == 2
    assert {item["impact"] for item in impacts} == {"direct"}

    deduction = await client.post(
        "/api/v2/deductions",
        json={"name": "固定修订推演", "scenarioTypeKey": "zc3"},
    )
    graph = {
        "nodes": [
            {"id": "start", "kind": "start", "name": "开始节点", "position": {"x": 0, "y": 0}},
            {
                "id": "branch-1",
                "kind": "branch-scheme",
                "branchSchemeId": first["id"],
                "branchSchemeName": "错误旧名称",
                "branchSchemeRevisionId": first_revision["id"],
                "revisionNumber": 999,
                "position": {"x": 200, "y": 0},
            },
            {
                "id": "branch-2",
                "kind": "branch-scheme",
                "branchSchemeId": second["id"],
                "branchSchemeName": second["name"],
                "branchSchemeRevisionId": second_revision["id"],
                "revisionNumber": 2,
                "position": {"x": 400, "y": 0},
            },
            {"id": "end", "kind": "end", "name": "结束节点", "position": {"x": 600, "y": 0}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start", "target": "branch-1"},
            {"id": "edge-2", "source": "branch-1", "target": "branch-2"},
            {"id": "edge-3", "source": "branch-2", "target": "end"},
        ],
    }
    updated = await client.put(
        f"/api/v2/deductions/{deduction.json()['id']}",
        json={"graph": graph, "status": "ready"},
    )
    assert updated.status_code == 200, updated.text
    fixed = updated.json()["graph"]["nodes"][1]
    assert fixed["branchSchemeName"] == "红方主方案"
    assert fixed["revisionNumber"] == 2

    newer = await client.post(
        f"/api/v2/branch-schemes/{first['id']}/revisions",
        json={"baseRevisionId": first_revision["id"], "description": "新发布版本"},
    )
    assert newer.status_code == 200
    fetched = (await client.get(f"/api/v2/deductions/{deduction.json()['id']}")).json()
    assert fetched["graph"]["nodes"][1]["branchSchemeRevisionId"] == first_revision["id"]
    assert (await client.delete(f"/api/v2/branch-schemes/{first['id']}")).status_code == 409


@pytest.mark.asyncio
async def test_duplicate_name_unknown_affiliation_and_unreferenced_delete(client: AsyncClient) -> None:
    branch = await create_branch(client, "Alpha")
    duplicate = await client.post(
        "/api/v2/branch-schemes",
        json={"name": "alpha", "scenarioTypeKey": "zc3", "sideKey": "red"},
    )
    unknown = await client.post(
        "/api/v2/branch-schemes",
        json={"name": "未知阵营", "scenarioTypeKey": "zc3", "sideKey": "missing"},
    )
    assert duplicate.status_code == 409
    assert unknown.status_code == 422
    assert (await client.delete(f"/api/v2/branch-schemes/{branch['id']}")).status_code == 204
