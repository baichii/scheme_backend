from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from backend.app.branch_scheme.schema.branch_scheme import GetBranchSchemeRevision
from backend.common.schema import SchemaBase

DecimalId = Annotated[str, StringConstraints(pattern=r"^[1-9]\d*$")]
DeductionRunStatus = Literal["starting", "running", "stopping", "finished", "failed", "stopped"]
DeductionTaskStatus = Literal["READY", "PENDING", "RUNNING", "STOPPING", "END", "ERROR"]
RuntimeMessageLevel = Literal["info", "warning", "error"]


class DeductionRunSchemaBase(SchemaBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class CreateDeductionRunParam(DeductionRunSchemaBase):
    deduction_id: DecimalId
    environment_resource_id: DecimalId


class GetEnvironmentRuntimeSnapshot(DeductionRunSchemaBase):
    status: Literal["healthy", "unhealthy"]
    checked_at: datetime
    container_ip: str | None = None
    container_port: int | None = None


class GetDeductionTask(DeductionRunSchemaBase):
    id: str
    kind: Literal["container", "agent"]
    branch_node_id: str
    branch_scheme_id: str
    branch_scheme_name: str
    name: str
    dependency_ids: list[str]
    status: DeductionTaskStatus
    parent_task_id: str | None = None
    source_node_id: str | None = None
    agent_resource_id: str | None = None
    agent_version_id: str | None = None
    agent_revision_number: int | None = None
    agent_checksum: str | None = None
    agent_name: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class GetDeductionBranchRuntime(DeductionRunSchemaBase):
    node_id: str
    branch_scheme_id: str
    branch_scheme_name: str
    dependency_node_ids: list[str]
    agent_task_ids: list[str]
    branch_scheme_revision_id: str | None = None
    revision_number: int | None = None
    snapshot: GetBranchSchemeRevision | None = None
    container_task_id: str | None = None


class GetDeductionRunSummary(DeductionRunSchemaBase):
    id: str
    deduction_id: str
    status: DeductionRunStatus
    environment_resource_id: str
    environment_name: str
    started_at: datetime
    updated_at: datetime
    ended_at: datetime | None = None


class GetDeductionRunSnapshot(GetDeductionRunSummary):
    sequence: int
    environment_runtime: GetEnvironmentRuntimeSnapshot
    sim_time: str
    situation: list[Any] = Field(default_factory=list)
    tasks: list[GetDeductionTask]
    branches: list[GetDeductionBranchRuntime]


class RuntimeMessageBase(DeductionRunSchemaBase):
    sequence: int = Field(ge=1)
    run_id: str
    emitted_at: datetime
    sim_time: str


class RuntimeRunStateMessage(RuntimeMessageBase):
    type: Literal["run_state"] = "run_state"
    status: DeductionRunStatus
    ended_at: datetime | None = None


class RuntimeTaskStateMessage(RuntimeMessageBase):
    type: Literal["task_state"] = "task_state"
    task_id: str
    status: DeductionTaskStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None


class RuntimeSimTimeMessage(RuntimeMessageBase):
    type: Literal["sim_time"] = "sim_time"
    health_or_not: bool
    container_ip: str | None = None
    container_port: int | None = None


class RuntimeAgentMessage(RuntimeMessageBase):
    level: RuntimeMessageLevel
    content: str
    task_id: str
    task_name: str
    branch_node_id: str
    branch_scheme_id: str
    branch_scheme_name: str


class RuntimeEventMessage(RuntimeAgentMessage):
    type: Literal["event"] = "event"
    title: str


class RuntimeLogMessage(RuntimeAgentMessage):
    type: Literal["log"] = "log"


RuntimeStreamMessage = Annotated[
    RuntimeRunStateMessage
    | RuntimeTaskStateMessage
    | RuntimeSimTimeMessage
    | RuntimeEventMessage
    | RuntimeLogMessage,
    Field(discriminator="type"),
]


class GetRuntimeEventPage(DeductionRunSchemaBase):
    items: list[RuntimeEventMessage]
    has_more: bool
    next_before_sequence: int | None = None


class GetRuntimeLogPage(DeductionRunSchemaBase):
    items: list[RuntimeLogMessage]
    has_more: bool
    next_before_sequence: int | None = None
