import json

from httpx import AsyncClient

from tests.resource_v2.helpers import agent_file


def metadata(**values: object) -> dict[str, tuple[None, str]]:
    return {"metadata": (None, json.dumps(values, ensure_ascii=False))}


async def create_agent(
    client: AsyncClient,
    name: str = "分支测试智能体",
    content: bytes | None = None,
) -> dict:
    response = await client.post(
        "/api/v2/resources",
        files={**metadata(type="agent", name=name), "file": ("agent.zip", content or agent_file())},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def create_branch(client: AsyncClient, name: str = "测试分支方案") -> dict:
    response = await client.post(
        "/api/v2/branch-schemes",
        json={
            "name": name,
            "description": "阶段 3 测试",
            "scenarioTypeKey": "zc3",
            "sideKey": "red",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def bind_default_graph(branch: dict, agent: dict) -> dict:
    graph = branch["graph"]
    version = agent["versions"][0]
    for node in graph["nodes"]:
        if node["scope"] != "task":
            continue
        node["agentBinding"] = {
            "resourceId": agent["id"],
            "resourceName": agent["name"],
            "agentVersionId": version["id"],
            "agentRevisionNumber": version["revisionNumber"],
            "parameters": {},
        }
    return graph


async def configure_branch(client: AsyncClient, branch: dict, agent: dict) -> dict:
    response = await client.post(
        f"/api/v2/branch-schemes/{branch['id']}/revisions",
        json={
            "baseRevisionId": branch["headRevisionId"],
            "status": "configured",
            "graph": bind_default_graph(branch, agent),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
