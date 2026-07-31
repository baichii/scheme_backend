import io
import json
import zipfile


def scenario_file(name: str = "zc3") -> bytes:
    return json.dumps(
        {
            "name": name,
            "description": "测试想定",
            "start_time": "2026-01-01 00:00:00",
            "end_time": "2026-01-01 01:00:00",
            "camps": [{"camp": "1", "sides": ["red"]}, {"camp": "2", "sides": ["blue"]}],
            "relationship": {"hostiles": {"red": ["blue"], "blue": ["red"]}},
        },
        ensure_ascii=False,
    ).encode()


def strategy_file(scenario: str = "zc3") -> bytes:
    return json.dumps(
        {
            "plan_id": "plan-1",
            "name": "测试策略",
            "scenario_name": scenario,
            "side": "red",
            "objective": "完成测试",
            "constraints": [],
            "branches": [{"branch_id": 1, "name": "主方案"}],
        },
        ensure_ascii=False,
    ).encode()


def agent_file(
    version: str = "1.0.0",
    extra: str = "",
    params: list[dict] | None = None,
) -> bytes:
    data = io.BytesIO()
    config = (
        f"PARAMS: {json.dumps(params or [], ensure_ascii=False)}\n"
        f"STATUS: [运行中, 已结束]\nVERSION: '{version}'\n{extra}"
    )
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("agent.py", "class Agent: pass\n")
        archive.writestr("config.yaml", config)
    return data.getvalue()
