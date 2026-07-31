import pytest
from pydantic import ValidationError

from backend.app.resource.schema.protocol import AgentConfig


def parameter(parameter_type: str, chinese_type: str, value, other=None) -> dict:
    result = {
        "name": f"test_{parameter_type}",
        "chineseName": f"测试{chinese_type}",
        "type": parameter_type,
        "chineseType": chinese_type,
        "description": "协议校验参数",
        "required": True,
        "defaultValue": value,
    }
    if other is not None:
        result["other"] = other
    return result


def test_accepts_complete_agent_v2_parameter_protocol() -> None:
    config = AgentConfig.model_validate(
        {
            "PARAMS": [
                parameter("string", "字符串", "目标"),
                parameter("int", "整数", 1),
                parameter("float", "浮点数", 0.5),
                parameter("datetime", "日期时间", "2026-03-03 09:00:00"),
                parameter("bool", "布尔类型", False),
                parameter("list", "列表", ["A1"]),
                parameter("table", "表格", [{"名称": "T1"}], {"col": ["名称"]}),
                parameter(
                    "choice",
                    "选择",
                    ["red"],
                    {
                        "multiple": True,
                        "valueType": "string",
                        "options": [{"label": "红方", "value": "red"}],
                    },
                ),
                parameter("area", "区域", [[[39.9, 116.3], [39.95, 116.35], [39.92, 116.4]]]),
                parameter(
                    "named_area",
                    "命名区域",
                    [{"禁飞区": [[39.8, 116.2], [39.82, 116.25], [39.79, 116.28]]}],
                ),
                parameter("route", "路径", [[[39.88, 116.2], [39.9, 116.28]]]),
            ],
            "STATUS": ["运行中", "已结束"],
            "VERSION": "0.1.0",
        }
    )
    assert len(config.PARAMS) == 11


@pytest.mark.parametrize(
    "invalid",
    [
        parameter("bool", "布尔值", True),
        parameter(
            "choice",
            "选择",
            1,
            {
                "multiple": False,
                "valueType": "string",
                "options": [{"label": "一", "value": 1}],
            },
        ),
        parameter("area", "区域", [[[91, 116.3], [39.95, 116.35], [39.92, 116.4]]]),
        parameter(
            "named_area",
            "命名区域",
            [
                {"区域": [[39.8, 116.2], [39.82, 116.25], [39.79, 116.28]]},
                {"区域": [[39.7, 116.1], [39.72, 116.15], [39.69, 116.18]]},
            ],
        ),
    ],
)
def test_rejects_agent_parameters_outside_v2_contract(invalid: dict) -> None:
    with pytest.raises(ValidationError):
        AgentConfig.model_validate(
            {"PARAMS": [invalid], "STATUS": ["运行中", "已结束"], "VERSION": "0.1.0"}
        )
