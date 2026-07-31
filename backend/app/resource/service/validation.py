import hashlib
import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

import yaml
from pydantic import ValidationError

from backend.app.resource.schema.protocol import AgentConfig, AgentParameter, ScenarioInput, StrategyConfig
from backend.app.resource.schema.resource import ValidationReport
from backend.common.exception import errors


@dataclass(frozen=True)
class ValidatedResourceFile:
    format: str
    parsed_data: dict
    report: ValidationReport
    checksum: str


def _unprocessable(message: str) -> errors.HTTPError:
    return errors.HTTPError(code=422, msg=message)


def validate_resource_file(
    resource_type: str, filename: str, content: bytes, scenario_names: set[str]
) -> ValidatedResourceFile:
    extension = Path(filename).suffix.lower().lstrip(".")
    accepted = {"scenario": {"json"}, "strategy": {"json", "yaml", "yml"}, "agent": {"zip"}}
    if extension not in accepted.get(resource_type, set()):
        raise _unprocessable(f"{resource_type} 不支持 .{extension or '未知'} 文件")
    checksum = hashlib.sha256(content).hexdigest()
    try:
        if resource_type == "agent":
            parsed, summary = _validate_agent(content)
            file_format = "ZIP"
        else:
            raw = json.loads(content) if extension == "json" else yaml.safe_load(content)
            if resource_type == "scenario":
                scenario = ScenarioInput.model_validate(raw)
                parsed = scenario.to_public()
                summary = {
                    "开始时间": parsed["startTime"],
                    "终止时间": parsed["endTime"],
                    "支持Side": " / ".join(parsed["supportedSides"]),
                    "阵营数量": len(parsed["camps"]),
                }
            else:
                strategy = StrategyConfig.model_validate(raw)
                if strategy.scenario_name not in scenario_names:
                    raise _unprocessable(f"未找到想定资源：{strategy.scenario_name}")
                parsed = strategy.model_dump(mode="json")
                summary = {
                    "想定": strategy.scenario_name,
                    "所属方": strategy.side,
                    "分支数量": len(strategy.branches),
                }
            file_format = extension.upper()
    except errors.HTTPError:
        raise
    except (ValidationError, ValueError, BadZipFile, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise _unprocessable(f"资源文件校验失败：{exc}") from exc
    return ValidatedResourceFile(
        format=file_format,
        parsed_data=parsed,
        checksum=checksum,
        report=ValidationReport(status="valid", issues=[], summary=summary),
    )


def _validate_agent(content: bytes) -> tuple[dict, dict[str, str | int]]:
    with ZipFile(BytesIO(content)) as archive:
        files = [
            name
            for name in archive.namelist()
            if not name.endswith("/") and not name.startswith("__MACOSX/")
        ]
        roots: dict[str, set[str]] = {}
        for name in files:
            parts = [part for part in name.split("/") if part]
            if len(parts) > 2 or parts[-1] not in {"agent.py", "config.yaml"}:
                continue
            root = "/".join(parts[:-1])
            roots.setdefault(root, set()).add(parts[-1])
        packages = [root for root, names in roots.items() if names == {"agent.py", "config.yaml"}]
        if len(packages) != 1:
            raise ValueError("智能体包根目录必须同时包含 agent.py 和 config.yaml")
        root = packages[0]
        config_path = f"{root}/config.yaml" if root else "config.yaml"
        parsed = AgentConfig.model_validate(yaml.safe_load(archive.read(config_path)))
        return parsed.model_dump(mode="json"), {
            "包根目录": root or "/",
            "入口文件": f"{root}/agent.py" if root else "agent.py",
            "配置文件": config_path,
            "参数数量": len(parsed.PARAMS),
            "状态数量": len(parsed.STATUS),
            "版本": parsed.VERSION,
        }


def validate_agent_parameter_value(parameter: AgentParameter, value: Any) -> bool:
    if value is None or value == "" or value == []:
        return not parameter.required
    try:
        AgentParameter.model_validate({**parameter.model_dump(), "defaultValue": value})
    except ValidationError:
        return False
    return True
