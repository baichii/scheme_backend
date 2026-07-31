from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from backend.common.schema import SchemaBase

ResourceType = Literal["scenario", "strategy", "agent", "environment"]
ResourceName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]
ResourceDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ResourceSchemaBase(SchemaBase):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, extra="forbid"
    )


class ValidationIssue(ResourceSchemaBase):
    level: Literal["error", "warning"]
    path: str
    message: str


class ValidationReport(ResourceSchemaBase):
    status: Literal["valid", "warning", "invalid"]
    issues: list[ValidationIssue]
    summary: dict[str, str | int | float]


class EnvironmentConfig(ResourceSchemaBase):
    template: str = Field(min_length=1)
    scenario_type_key: str = Field(min_length=1)
    values: dict[str, str | int | bool]


class CreateResourceParam(ResourceSchemaBase):
    type: ResourceType
    name: ResourceName = ""
    description: ResourceDescription | None = None
    version: str | None = None
    environment: EnvironmentConfig | None = None


class ResourceVersionDetail(ResourceSchemaBase):
    id: str
    version: str
    revision_number: int | None = None
    package_version: str | None = None
    format: str
    file_name: str | None = None
    size: int | None = None
    checksum: str | None = None
    download_url: str | None = None
    parsed_data: Any = None
    protocol_migration_error: str | None = None
    validation: ValidationReport
    created_at: datetime


class GetResourceSummary(ResourceSchemaBase):
    id: str
    name: str
    description: str | None = None
    type: ResourceType
    archived: bool = False
    updated_at: datetime
    current_version: str | None = None
    current_version_id: str | None = None
    format: str | None = None
    version_count: int | None = None
    environment: EnvironmentConfig | None = None


class GetResourceDetail(GetResourceSummary):
    versions: list[ResourceVersionDetail]
    created_at: datetime


class GetResourcePage(ResourceSchemaBase):
    items: list[GetResourceSummary]
    total: int
    page: int
    page_size: int


class AgentBranchReference(ResourceSchemaBase):
    branch_scheme_id: str
    branch_scheme_name: str
    branch_status: Literal["draft", "configured"]
    base_revision_id: str
    base_revision_number: int
    published_revision_id: str | None = None
    current_agent_version_id: str
    current_agent_revision_number: int
    target_agent_version_id: str
    target_agent_revision_number: int
    node_ids: list[str]
    impact: Literal["direct", "defaults", "review", "draft-conflict", "current"]
    reasons: list[str]


class GetAgentVersionImpact(ResourceSchemaBase):
    resource_id: str
    resource_name: str
    target_version_id: str
    target_revision_number: int
    references: list[AgentBranchReference]
    historical_reference_count: int


class AgentReplacementResult(ResourceSchemaBase):
    resource: GetResourceDetail
    version: ResourceVersionDetail
    package_version_unchanged: bool
    impact: GetAgentVersionImpact


class GetEnvironmentRuntime(ResourceSchemaBase):
    status: Literal["connected", "disconnected", "error"]
    environment_time: datetime | None = None


class CreateResourceInternal(SchemaBase):
    id: int
    type: str
    name: str
    normalized_name: str
    description: str | None = None
    current_version_id: int | None = None
    archived: bool = False
    environment: dict | None = None


class CreateResourceVersionInternal(SchemaBase):
    id: int
    resource_id: int
    version: str
    revision_number: int | None = None
    package_version: str | None = None
    format: str
    file_name: str | None = None
    size: int | None = None
    checksum: str | None = None
    object_key: str | None = None
    parsed_data: dict | list | None = None
    validation: dict
