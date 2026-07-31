from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, StringConstraints, model_validator
from pydantic.alias_generators import to_camel

from backend.common.schema import SchemaBase

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
NonEmpty = Annotated[str, StringConstraints(min_length=1)]
BranchSchemeStatus = Literal["draft", "configured"]


class BranchSchemeSchemaBase(SchemaBase):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, extra="forbid"
    )


class BranchPosition(BranchSchemeSchemaBase):
    x: float
    y: float


class AgentBinding(BranchSchemeSchemaBase):
    resource_id: NonEmpty
    resource_name: NonEmpty
    agent_version_id: NonEmpty
    agent_revision_number: int = Field(ge=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class BranchNode(BranchSchemeSchemaBase):
    id: NonEmpty
    kind: Literal["start", "action", "decision", "result"]
    scope: Literal["terminal", "task", "planning"]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=48)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    mark: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4)]
    catalog_key: NonEmpty | None = None
    position: BranchPosition
    agent_binding: AgentBinding | None = None
    trigger: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "BranchNode":
        terminal = self.kind in {"start", "result"}
        if terminal != (self.scope == "terminal"):
            raise ValueError("初始和预期节点必须属于 terminal，其他节点不能属于 terminal")
        if self.scope != "task" and self.agent_binding:
            raise ValueError("只有任务节点可以绑定智能体")
        return self


class BranchEdge(BranchSchemeSchemaBase):
    id: NonEmpty
    source: NonEmpty
    target: NonEmpty
    source_handle: Literal["right-out", "top-out", "bottom-out"] | None = None
    target_handle: Literal["left-in", "top-in", "bottom-in"] | None = None


class BranchViewport(BranchPosition):
    zoom: float = Field(ge=0.1, le=4)


class BranchSchemeGraph(BranchSchemeSchemaBase):
    nodes: list[BranchNode]
    edges: list[BranchEdge]
    viewport: BranchViewport | None = None

    @model_validator(mode="after")
    def validate_graph(self) -> "BranchSchemeGraph":
        node_ids = [node.id for node in self.nodes]
        edge_ids = [edge.id for edge in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("节点 ID 不可重复")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("连线 ID 不可重复")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ValueError("连线引用了不存在的节点")
            if edge.source == edge.target:
                raise ValueError("节点不能连接到自身")
        return self


class BranchSchemeOrigin(BranchSchemeSchemaBase):
    type: Literal["ai-iteration"]
    ai_iteration_id: NonEmpty
    run_id: NonEmpty
    round_number: int = Field(ge=1)


class CreateBranchSchemeParam(BranchSchemeSchemaBase):
    name: Name
    description: Description = ""
    scenario_type_key: NonEmpty
    side_key: NonEmpty


class UpdateBranchSchemeParam(BranchSchemeSchemaBase):
    name: Name | None = None
    description: Description | None = None
    status: BranchSchemeStatus | None = None
    graph: BranchSchemeGraph | None = None


class CreateBranchSchemeRevisionParam(UpdateBranchSchemeParam):
    base_revision_id: NonEmpty


class GetBranchSchemeRevision(BranchSchemeSchemaBase):
    id: str
    branch_scheme_id: str
    revision_number: int
    parent_revision_id: str | None = None
    name: str
    description: str
    scenario_type_key: str
    side_key: str
    status: BranchSchemeStatus
    created_by: str
    origin: BranchSchemeOrigin | None = None
    graph: BranchSchemeGraph
    created_at: datetime


class GetBranchSchemeDetail(BranchSchemeSchemaBase):
    id: str
    name: str
    description: str
    scenario_type_key: str
    side_key: str
    status: BranchSchemeStatus
    created_by: str
    origin: BranchSchemeOrigin | None = None
    graph: BranchSchemeGraph
    head_revision_id: str
    head_revision_number: int
    published_revision_id: str | None = None
    published_revision_number: int | None = None
    created_at: datetime
    updated_at: datetime


class GetBranchSchemeSummary(BranchSchemeSchemaBase):
    id: str
    name: str
    description: str
    scenario_type_key: str
    side_key: str
    status: BranchSchemeStatus
    head_revision_id: str
    head_revision_number: int
    published_revision_id: str | None = None
    published_revision_number: int | None = None
    has_draft: bool
    node_count: int
    created_by: str
    origin: BranchSchemeOrigin | None = None
    updated_at: datetime


class GetBranchSchemePage(BranchSchemeSchemaBase):
    items: list[GetBranchSchemeSummary]
    total: int
    page: int
    page_size: int


class GetBranchSchemeRevisionSummary(BranchSchemeSchemaBase):
    id: str
    branch_scheme_id: str
    revision_number: int
    parent_revision_id: str | None = None
    status: BranchSchemeStatus
    created_by: str
    created_at: datetime


def get_default_branch_scheme_graph() -> BranchSchemeGraph:
    return BranchSchemeGraph.model_validate(
        {
            "nodes": [
                {
                    "id": "start",
                    "name": "初始节点",
                    "kind": "start",
                    "scope": "terminal",
                    "mark": "起",
                    "description": "分支方案进入执行状态",
                    "position": {"x": 20, "y": 235},
                },
                {
                    "id": "decision",
                    "name": "目标是否确认",
                    "kind": "decision",
                    "scope": "task",
                    "mark": "判",
                    "description": "依据侦察结果选择后续路径",
                    "position": {"x": 250, "y": 235},
                },
                {
                    "id": "strike",
                    "name": "联合打击",
                    "kind": "action",
                    "scope": "task",
                    "mark": "火压",
                    "catalogKey": "fire_suppression",
                    "description": "按迭代配置执行目标压制",
                    "position": {"x": 500, "y": 95},
                },
                {
                    "id": "recheck",
                    "name": "补充侦察",
                    "kind": "action",
                    "scope": "task",
                    "mark": "空侦",
                    "catalogKey": "long_range_recon",
                    "description": "目标不明确时扩大侦察范围",
                    "position": {"x": 500, "y": 375},
                },
                {
                    "id": "result",
                    "name": "预期节点",
                    "kind": "result",
                    "scope": "terminal",
                    "mark": "果",
                    "description": "各行动分支在此汇合",
                    "position": {"x": 760, "y": 235},
                },
            ],
            "edges": [
                {"id": "edge-start-decision", "source": "start", "target": "decision"},
                {"id": "edge-decision-strike", "source": "decision", "target": "strike"},
                {"id": "edge-decision-recheck", "source": "decision", "target": "recheck"},
                {"id": "edge-strike-result", "source": "strike", "target": "result"},
                {"id": "edge-recheck-result", "source": "recheck", "target": "result"},
            ],
        }
    )
