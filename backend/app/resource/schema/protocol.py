from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase


class AgentParameter(SchemaBase):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1)
    chineseName: str = Field(min_length=1)
    type: Literal[
        "string",
        "int",
        "float",
        "datetime",
        "bool",
        "list",
        "table",
        "choice",
        "area",
        "named_area",
        "route",
    ]
    chineseType: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool
    defaultValue: Any = None
    other: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_default(self) -> "AgentParameter":
        labels = {
            "string": "字符串",
            "int": "整数",
            "float": "浮点数",
            "datetime": "日期时间",
            "bool": "布尔类型",
            "list": "列表",
            "table": "表格",
            "choice": "选择",
            "area": "区域",
            "named_area": "命名区域",
            "route": "路径",
        }
        if self.chineseType != labels[self.type]:
            raise ValueError(f"chineseType must be {labels[self.type]} for {self.type}")
        if self.type not in {"table", "choice"} and self.other is not None:
            raise ValueError(f"{self.type} parameter must not define other")
        value = self.defaultValue
        valid = value is None
        if self.type == "string":
            valid = valid or isinstance(value, str)
        elif self.type == "int":
            valid = valid or isinstance(value, int) and not isinstance(value, bool)
        elif self.type == "float":
            valid = valid or isinstance(value, (int, float)) and not isinstance(value, bool)
        elif self.type == "bool":
            valid = valid or isinstance(value, bool)
        elif self.type == "list":
            valid = valid or isinstance(value, list)
        elif self.type == "table":
            valid = valid or isinstance(value, list) and all(isinstance(row, dict) for row in value)
            other = self.other or {}
            if set(other) != {"col"}:
                raise ValueError("table parameter other must contain only col")
            columns = other.get("col")
            if (
                not isinstance(columns, list)
                or not columns
                or any(not isinstance(column, str) or not column.strip() for column in columns)
                or len(columns) != len(set(columns))
            ):
                raise ValueError("table parameter requires unique other.col values")
            if value is not None and any(set(row) != set(columns) for row in value):
                raise ValueError("table rows must contain exactly the declared columns")
        elif self.type == "choice":
            other = self.other or {}
            if set(other) != {"multiple", "valueType", "options"}:
                raise ValueError("choice parameter other fields are incomplete")
            multiple = other.get("multiple")
            value_type = other.get("valueType")
            options = other.get("options")
            if not isinstance(multiple, bool) or value_type not in {"string", "int"}:
                raise ValueError("choice parameter multiple/valueType is invalid")
            if not isinstance(options, list) or not options:
                raise ValueError("choice parameter requires options")
            if any(
                not isinstance(option, dict)
                or set(option) != {"label", "value"}
                or not isinstance(option["label"], str)
                or not option["label"].strip()
                for option in options
            ):
                raise ValueError("choice options must contain non-empty label and value")
            option_values = [option["value"] for option in options]
            option_labels = [option["label"] for option in options]
            expected = str if value_type == "string" else int
            if any(not isinstance(item, expected) or isinstance(item, bool) for item in option_values):
                raise ValueError("choice option values do not match valueType")
            typed_values = {(type(item).__name__, item) for item in option_values}
            if len(option_labels) != len(set(option_labels)) or len(option_values) != len(typed_values):
                raise ValueError("choice option labels and values must be unique")
            valid = valid or (
                isinstance(value, list) and all(item in option_values for item in value)
                if multiple
                else value in option_values
            )
            if value is not None and multiple != isinstance(value, list):
                valid = False
            if isinstance(value, list) and len(value) != len(
                {(type(item).__name__, item) for item in value}
            ):
                valid = False
        elif self.type in {"area", "named_area", "route"}:
            valid = valid or _validate_geospatial_value(self.type, value)
        elif self.type == "datetime":
            if isinstance(value, str):
                try:
                    datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    valid = True
                except ValueError:
                    valid = False
        if not valid:
            raise ValueError(f"invalid defaultValue for parameter type {self.type}")
        return self


def _valid_coordinate(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
        and -90 <= value[0] <= 90
        and -180 <= value[1] <= 180
    )


def _valid_line(value: Any, minimum: int) -> bool:
    return (
        isinstance(value, list) and len(value) >= minimum and all(_valid_coordinate(item) for item in value)
    )


def _validate_geospatial_value(parameter_type: str, value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    if parameter_type == "area":
        return all(_valid_line(polygon, 3) for polygon in value)
    if parameter_type == "route":
        return all(_valid_line(line, 2) for line in value)
    names: list[str] = []
    for item in value:
        if not isinstance(item, dict) or len(item) != 1:
            return False
        name, polygon = next(iter(item.items()))
        if not isinstance(name, str) or not name.strip() or not _valid_line(polygon, 3):
            return False
        names.append(name)
    return len(names) == len(set(names))


class AgentConfig(SchemaBase):
    model_config = ConfigDict(extra="ignore")

    PARAMS: list[AgentParameter]
    STATUS: list[str] = Field(min_length=1)
    VERSION: str = Field(pattern=r"^\d+(?:\.\d+){1,2}(?:[-+][0-9A-Za-z.-]+)?$")

    @model_validator(mode="after")
    def validate_unique_values(self) -> "AgentConfig":
        names = [parameter.name for parameter in self.PARAMS]
        if len(names) != len(set(names)):
            raise ValueError("agent parameter names must be unique")
        if any(not status.strip() for status in self.STATUS):
            raise ValueError("agent statuses must not be empty")
        return self


class ScenarioCamp(SchemaBase):
    camp: str | int
    sides: list[str] = Field(min_length=1)


class ScenarioInput(SchemaBase):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    start_time: str
    end_time: str
    camps: list[ScenarioCamp] = Field(min_length=1)
    relationship: dict[str, Any]

    @model_validator(mode="after")
    def validate_scenario(self) -> "ScenarioInput":
        def parse(value: str) -> datetime:
            return datetime.fromisoformat(value.replace(" ", "T"))

        if parse(self.start_time) >= parse(self.end_time):
            raise ValueError("scenario end_time must be later than start_time")
        camp_ids = [str(camp.camp) for camp in self.camps]
        sides = [side for camp in self.camps for side in camp.sides]
        if len(camp_ids) != len(set(camp_ids)) or len(sides) != len(set(sides)):
            raise ValueError("scenario camps and sides must be unique")
        hostiles = self.relationship.get("hostiles", {})
        if not isinstance(hostiles, dict):
            raise ValueError("scenario relationship.hostiles must be an object")
        known = set(sides)
        if any(
            source not in known or any(target not in known for target in targets)
            for source, targets in hostiles.items()
        ):
            raise ValueError("scenario hostile relationship uses unknown sides")
        return self

    def to_public(self) -> dict[str, Any]:
        hostiles = self.relationship.get("hostiles", {})
        return {
            "name": self.name,
            "description": self.description,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "camps": [{"camp": str(camp.camp), "sides": camp.sides} for camp in self.camps],
            "supportedSides": [side for camp in self.camps for side in camp.sides],
            "relationships": {"hostiles": hostiles},
        }


class StrategyBranch(SchemaBase):
    model_config = ConfigDict(extra="allow")

    branch_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str = ""
    platform: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] | None = None


class StrategyConfig(SchemaBase):
    model_config = ConfigDict(extra="allow")

    plan_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    scenario_name: str = Field(min_length=1)
    side: str = Field(min_length=1)
    opponent_side: str = ""
    objective: str = Field(min_length=1)
    constraints: list[str]
    branches: list[StrategyBranch] = Field(min_length=1)
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_unique_branches(self) -> "StrategyConfig":
        ids = [branch.branch_id for branch in self.branches]
        if len(ids) != len(set(ids)):
            raise ValueError("strategy branch IDs must be unique")
        return self
