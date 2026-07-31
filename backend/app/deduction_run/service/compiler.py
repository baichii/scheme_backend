from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from backend.app.branch_scheme.model.branch_scheme import BranchSchemeRevision
from backend.app.branch_scheme.schema.branch_scheme import BranchNode, BranchSchemeGraph
from backend.app.configuration.schema.configuration import EnvironmentTemplateDocument
from backend.app.deduction.model.deduction import Deduction
from backend.app.deduction.schema.deduction import DeductionBranchSchemeNode, DeductionGraph
from backend.app.resource.model.resource import Resource, ResourceVersion
from backend.engine.schemas import (
    EngineAgentConfig,
    EngineBizValue,
    EngineCreateRequest,
    EngineEnvironmentConfig,
    EnginePinConfig,
    EngineQueueConfig,
    EngineTaskDefinition,
)
from backend.utils.snowflake import snowflake


@dataclass(frozen=True)
class PreparedAgent:
    node: BranchNode
    resource: Resource
    version: ResourceVersion


@dataclass(frozen=True)
class PreparedBranch:
    node: DeductionBranchSchemeNode
    revision: BranchSchemeRevision
    graph: BranchSchemeGraph
    agents: dict[str, PreparedAgent]


@dataclass(frozen=True)
class CompiledDeductionRun:
    engine_request: EngineCreateRequest
    task_values: list[dict]
    branches: list[dict]


def _can_reach(origin: str, target: str, adjacency: dict[str, list[str]]) -> bool:
    pending = [origin]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, []))
    return False


def _activation(parts: list[str]) -> str | None:
    return " AND ".join(parts) if parts else None


def _snapshot(revision: BranchSchemeRevision, graph: BranchSchemeGraph) -> dict:
    return {
        "id": str(revision.id),
        "branchSchemeId": str(revision.branch_scheme_id),
        "revisionNumber": revision.revision_number,
        "parentRevisionId": str(revision.parent_revision_id) if revision.parent_revision_id else None,
        "name": revision.name,
        "description": revision.description,
        "scenarioTypeKey": revision.scenario_type_key,
        "sideKey": revision.side_key,
        "status": revision.status,
        "createdBy": revision.created_by,
        "origin": revision.origin,
        "graph": graph.model_dump(mode="json", by_alias=True, exclude_none=True),
        "createdAt": revision.create_at.isoformat(),
    }


def compile_deduction_run(
    *,
    run_id: int,
    deduction: Deduction,
    graph: DeductionGraph,
    environment: Resource,
    environment_template: EnvironmentTemplateDocument,
    branches: list[PreparedBranch],
    resource_base_url: str,
    id_factory: Callable[[], int] = snowflake.generate,
) -> CompiledDeductionRun:
    """把固定版本的业务快照编译为 Matrix create 请求。"""

    branch_by_node = {branch.node.id: branch for branch in branches}
    branch_nodes = [node for node in graph.nodes if node.kind == "branch-scheme"]
    container_id_by_node = {node.id: id_factory() for node in branch_nodes}
    branch_dependencies = {
        node.id: [
            edge.source
            for edge in graph.edges
            if edge.target == node.id and edge.source in container_id_by_node
        ]
        for node in branch_nodes
    }
    environment_values = dict((environment.environment or {}).get("values", {}))
    env_config = EngineEnvironmentConfig(
        envType=environment_template.key,
        envInstanceConfig=environment_values,
    )
    dispatch = environment_template.runtime["dispatch_queue"]
    sim_time = environment_template.runtime["simulation_time_queue"]

    def biz_value(task_id: int) -> EngineBizValue:
        return EngineBizValue(
            dispatchQueue=EngineQueueConfig(name=dispatch.name, durable=dispatch.durable),
            simTimeQueue=EngineQueueConfig(name=sim_time.name, durable=sim_time.durable),
            deduceID=str(run_id),
            deduceTaskID=str(task_id),
        )

    definitions: list[EngineTaskDefinition] = []
    task_values: list[dict] = []
    runtime_branches: list[dict] = []
    base_url = resource_base_url.rstrip("/")

    for branch_node in branch_nodes:
        prepared = branch_by_node[branch_node.id]
        container_id = container_id_by_node[branch_node.id]
        dependency_node_ids = branch_dependencies[branch_node.id]
        container_dependency_ids = [container_id_by_node[node_id] for node_id in dependency_node_ids]
        definitions.append(
            EngineTaskDefinition(
                isRoot=not container_dependency_ids,
                isBox=True,
                id=str(container_id),
                envConfig=env_config.model_copy(deep=True),
                agentConfig=EngineAgentConfig(
                    deduceId=str(run_id),
                    taskId=str(container_id),
                    taskName=prepared.revision.name,
                ),
                bizValue=biz_value(container_id),
                pin=EnginePinConfig(
                    activate=_activation([f"{task_id}:3" for task_id in container_dependency_ids])
                ),
            )
        )
        task_values.append(
            {
                "id": container_id,
                "run_id": run_id,
                "kind": "container",
                "branch_node_id": branch_node.id,
                "branch_scheme_id": prepared.revision.branch_scheme_id,
                "branch_scheme_name": prepared.revision.name,
                "name": prepared.revision.name,
                "dependency_ids": container_dependency_ids,
                "status": "READY",
            }
        )

        task_nodes = [node for node in prepared.graph.nodes if node.scope == "task" and node.agent_binding]
        task_id_by_node = {node.id: id_factory() for node in task_nodes}
        adjacency: dict[str, list[str]] = {}
        for edge in prepared.graph.edges:
            adjacency.setdefault(edge.source, []).append(edge.target)

        agent_task_ids: list[str] = []
        for node in task_nodes:
            agent = prepared.agents[node.id]
            task_id = task_id_by_node[node.id]
            dependency_ids = [
                task_id_by_node[candidate.id]
                for candidate in task_nodes
                if candidate.id != node.id and _can_reach(candidate.id, node.id, adjacency)
            ]
            activation_parts = [f"{container_id}:1", *[f"{value}:3" for value in dependency_ids]]
            filename = agent.version.file_name or ""
            definitions.append(
                EngineTaskDefinition(
                    isRoot=False,
                    isBox=False,
                    id=str(task_id),
                    envConfig=env_config.model_copy(deep=True),
                    agentLoad=Path(filename).stem,
                    agentUrl=(
                        f"{base_url}/api/v2/resources/{agent.resource.id}/versions/{agent.version.id}/file"
                    ),
                    agentConfig=EngineAgentConfig(
                        deduceId=str(run_id),
                        taskId=str(task_id),
                        taskName=node.name,
                        agentInstanceConfig=dict(node.agent_binding.parameters),
                    ),
                    bizValue=biz_value(task_id),
                    pin=EnginePinConfig(activate=_activation(activation_parts)),
                    father=str(container_id),
                )
            )
            task_values.append(
                {
                    "id": task_id,
                    "run_id": run_id,
                    "kind": "agent",
                    "branch_node_id": branch_node.id,
                    "branch_scheme_id": prepared.revision.branch_scheme_id,
                    "branch_scheme_name": prepared.revision.name,
                    "name": node.name,
                    "dependency_ids": dependency_ids,
                    "status": "READY",
                    "parent_task_id": container_id,
                    "source_node_id": node.id,
                    "agent_resource_id": agent.resource.id,
                    "agent_version_id": agent.version.id,
                    "agent_revision_number": agent.version.revision_number,
                    "agent_checksum": agent.version.checksum,
                    "agent_name": agent.resource.name,
                    "agent_parameters": dict(node.agent_binding.parameters),
                }
            )
            agent_task_ids.append(str(task_id))

        runtime_branches.append(
            {
                "nodeId": branch_node.id,
                "branchSchemeId": str(prepared.revision.branch_scheme_id),
                "branchSchemeName": prepared.revision.name,
                "branchSchemeRevisionId": str(prepared.revision.id),
                "revisionNumber": prepared.revision.revision_number,
                "snapshot": _snapshot(prepared.revision, prepared.graph),
                "dependencyNodeIds": dependency_node_ids,
                "containerTaskId": str(container_id),
                "agentTaskIds": agent_task_ids,
            }
        )

    return CompiledDeductionRun(
        engine_request=EngineCreateRequest(body=definitions),
        task_values=task_values,
        branches=runtime_branches,
    )
