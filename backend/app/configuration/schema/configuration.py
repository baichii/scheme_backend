from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints, model_validator
from pydantic.alias_generators import to_camel

from backend.common.schema import SchemaBase

Key = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ConfigurationDocumentBase(SchemaBase):
    model_config = ConfigDict(extra="forbid")


class ConfigurationSchemaBase(SchemaBase):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, extra="forbid"
    )


class QueueDocument(ConfigurationDocumentBase):
    name: NonEmpty
    durable: bool


class EnvironmentTemplateField(ConfigurationDocumentBase):
    key: Key
    label: NonEmpty
    type: Literal["ipv4", "integer", "select"]
    required: bool
    default: str | int | None
    minimum: int | None = None
    maximum: int | None = None
    options: list[str] | None = None

    @model_validator(mode="after")
    def validate_type_options(self) -> "EnvironmentTemplateField":
        if self.type == "integer" and (
            self.minimum is None or self.maximum is None or self.minimum > self.maximum
        ):
            raise ValueError("integer field requires a valid minimum and maximum")
        if self.type == "select" and (
            not self.options or not isinstance(self.default, str) or self.default not in self.options
        ):
            raise ValueError("select field default must be included in options")
        return self


class EnvironmentTemplateDocument(ConfigurationDocumentBase):
    schema_version: Literal[1]
    kind: Literal["environment_template"]
    key: Key
    name: NonEmpty
    description: NonEmpty
    fields: list[EnvironmentTemplateField] = Field(min_length=1)
    runtime: dict[str, QueueDocument]

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "EnvironmentTemplateDocument":
        if len({field.key for field in self.fields}) != len(self.fields):
            raise ValueError("environment template field keys must be unique")
        if set(self.runtime) != {"dispatch_queue", "simulation_time_queue"}:
            raise ValueError("environment runtime queues are incomplete")
        return self


class GetEnvironmentTemplate(ConfigurationSchemaBase):
    key: str
    name: str
    description: str
    fields: list[EnvironmentTemplateField]


class ScenarioSideDocument(ConfigurationDocumentBase):
    key: NonEmpty
    name: NonEmpty


class ScenarioTypeDocument(ConfigurationDocumentBase):
    schema_version: Literal[1]
    kind: Literal["scenario_type"]
    key: Key
    name: NonEmpty
    description: NonEmpty
    environment_templates: list[Key] = Field(min_length=1)
    scenarios: list[NonEmpty] = Field(min_length=1)
    sides: list[ScenarioSideDocument] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_values(self) -> "ScenarioTypeDocument":
        for values, label in (
            (self.environment_templates, "environment_templates"),
            (self.scenarios, "scenarios"),
            ([side.key for side in self.sides], "sides"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} must not contain duplicates")
        return self


class GetScenarioTypeSide(ConfigurationSchemaBase):
    key: str
    name: str


class GetScenarioType(ConfigurationSchemaBase):
    key: str
    name: str
    description: str
    environment_template_keys: list[str]
    scenarios: list[str]
    default_side_key: str
    sides: list[GetScenarioTypeSide]


class ConfigurationCatalog(ConfigurationDocumentBase):
    schema_version: Literal[1]
    environment_templates: list[Key] = Field(min_length=1)
    scenario_types: list[Key] = Field(min_length=1)
