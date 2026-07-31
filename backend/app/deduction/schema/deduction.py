from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic.alias_generators import to_camel

from backend.app.deduction_run.schema.deduction_run import (
    DeductionRunStatus,
    GetDeductionRunSummary,
)
from backend.common.schema import SchemaBase

TrimmedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
TrimmedDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
DeductionStatus = Literal["draft", "ready"]


class DeductionSchemaBase(SchemaBase):
    """推演方案 V2 schema 基类。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        allow_inf_nan=False,
    )


class DeductionPosition(DeductionSchemaBase):
    """推演节点坐标。"""

    x: float
    y: float


class DeductionViewport(DeductionPosition):
    """推演画布视口。"""

    zoom: float = Field(ge=0.1, le=4)


class DeductionTerminalNode(DeductionSchemaBase):
    """推演开始或结束节点。"""

    id: NonEmptyString
    kind: Literal["start", "end"]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=48)]
    position: DeductionPosition


class DeductionBranchSchemeNode(DeductionSchemaBase):
    """推演分支方案节点。"""

    id: NonEmptyString
    kind: Literal["branch-scheme"]
    branch_scheme_id: NonEmptyString
    branch_scheme_name: TrimmedName
    branch_scheme_revision_id: NonEmptyString
    revision_number: int = Field(ge=1)
    position: DeductionPosition


DeductionNode = Annotated[
    DeductionTerminalNode | DeductionBranchSchemeNode,
    Field(discriminator="kind"),
]


class DeductionEdge(DeductionSchemaBase):
    """推演节点连线。"""

    id: NonEmptyString
    source: NonEmptyString
    target: NonEmptyString
    source_handle: Literal["right-out", "top-out", "bottom-out"] | None = None
    target_handle: Literal["left-in", "top-in", "bottom-in"] | None = None


class DeductionGraph(DeductionSchemaBase):
    """推演画布。"""

    nodes: list[DeductionNode]
    edges: list[DeductionEdge]
    viewport: DeductionViewport | None = None

    @model_validator(mode="after")
    def validate_graph(self) -> "DeductionGraph":
        node_ids = [node.id for node in self.nodes]
        edge_ids = [edge.id for edge in self.edges]
        connections = [(edge.source, edge.target) for edge in self.edges]
        branch_nodes = [node for node in self.nodes if node.kind == "branch-scheme"]
        starts = [node for node in self.nodes if node.kind == "start"]
        ends = [node for node in self.nodes if node.kind == "end"]

        if len(set(node_ids)) != len(node_ids):
            raise ValueError("推演节点 ID 不可重复")
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("推演连线 ID 不可重复")
        if len(set(connections)) != len(connections):
            raise ValueError("同一对推演节点之间不能重复连接")
        if len(starts) != 1 or len(ends) != 1:
            raise ValueError("推演画布必须包含唯一的开始节点和结束节点")
        branch_ids = [node.branch_scheme_id for node in branch_nodes]
        if len(set(branch_ids)) != len(branch_ids):
            raise ValueError("同一分支方案只能加入一次")

        node_by_id = {node.id: node for node in self.nodes}
        for edge in self.edges:
            source = node_by_id.get(edge.source)
            target = node_by_id.get(edge.target)
            if source is None or target is None:
                raise ValueError("推演连线引用了不存在的节点")
            valid = source.id != target.id and (
                (source.kind == "start" and target.kind == "branch-scheme")
                or (source.kind == "branch-scheme" and target.kind == "branch-scheme")
                or (source.kind == "branch-scheme" and target.kind == "end")
            )
            if not valid:
                raise ValueError("推演连线必须沿“开始 → 分支方案 → 结束”方向连接")
            if source.kind == "start" and edge.source_handle not in (None, "right-out"):
                raise ValueError("开始节点只允许从右侧连接")
            if target.kind == "end" and edge.target_handle not in (None, "left-in"):
                raise ValueError("结束节点只允许从左侧连接")
        return self


def get_default_deduction_graph() -> DeductionGraph:
    """获取新建推演方案的默认画布。"""

    return DeductionGraph.model_validate(
        {
            "nodes": [
                {"id": "start", "kind": "start", "name": "开始节点", "position": {"x": 60, "y": 260}},
                {"id": "end", "kind": "end", "name": "结束节点", "position": {"x": 780, "y": 260}},
            ],
            "edges": [],
        }
    )


def validate_ready_deduction_graph(graph: DeductionGraph) -> None:
    """校验 ready 状态推演方案的分支数量和连通性。"""

    branch_nodes = [node for node in graph.nodes if node.kind == "branch-scheme"]
    if len(branch_nodes) < 2:
        raise ValueError("可运行推演至少需要两个分支方案")

    outgoing: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}
    for edge in graph.edges:
        outgoing.setdefault(edge.source, []).append(edge.target)
        incoming.setdefault(edge.target, []).append(edge.source)

    def reachable(origin: str, adjacency: dict[str, list[str]]) -> set[str]:
        reached: set[str] = set()
        pending = [origin]
        while pending:
            node_id = pending.pop()
            if node_id in reached:
                continue
            reached.add(node_id)
            pending.extend(adjacency.get(node_id, []))
        return reached

    from_start = reachable("start", outgoing)
    to_end = reachable("end", incoming)
    for node in branch_nodes:
        if node.id not in from_start or node.id not in to_end:
            raise ValueError(f"分支方案“{node.branch_scheme_name}”必须同时连接开始节点和结束节点")


class CreateDeductionParam(DeductionSchemaBase):
    """创建推演方案参数。"""

    name: TrimmedName
    description: TrimmedDescription = ""
    scenario_type_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CreateDeductionInternal(SchemaBase):
    """创建推演方案内部参数。"""

    name: str
    normalized_name: str
    description: str
    scenario_type_key: str
    status: DeductionStatus
    graph: dict
    created_by: str


class UpdateDeductionParam(DeductionSchemaBase):
    """更新推演方案参数。"""

    name: TrimmedName | None = None
    description: TrimmedDescription | None = None
    status: DeductionStatus | None = None
    graph: DeductionGraph | None = None

    @model_validator(mode="after")
    def reject_null_values(self) -> "UpdateDeductionParam":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{to_camel(field_name)} 不能为 null")
        return self


class GetDeductionDetail(DeductionSchemaBase):
    """推演方案详情。"""

    id: str
    name: str
    description: str
    scenario_type_key: str
    status: DeductionStatus
    graph: DeductionGraph
    created_by: str
    created_at: datetime
    updated_at: datetime
    latest_run: GetDeductionRunSummary | None = None


class GetDeductionSummary(DeductionSchemaBase):
    """推演方案摘要。"""

    id: str
    name: str
    description: str
    scenario_type_key: str
    status: DeductionStatus
    branch_scheme_count: int
    created_by: str
    updated_at: datetime
    latest_run: GetDeductionRunSummary | None = None


class GetDeductionPage(DeductionSchemaBase):
    """推演方案分页结果。"""

    items: list[GetDeductionSummary]
    total: int
    page: int
    page_size: int


class GetDeductionListParam(DeductionSchemaBase):
    """查询推演方案列表参数。"""

    status: DeductionStatus | Literal["all"] = "all"
    run_status: DeductionRunStatus | Literal["all"] = "all"
    search: str = ""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=100)
    sort_order: Literal["asc", "desc"] = "desc"

    @field_validator("search")
    @classmethod
    def trim_search(cls, value: str) -> str:
        return value.strip()
