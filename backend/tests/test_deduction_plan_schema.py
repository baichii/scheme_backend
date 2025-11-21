from datetime import datetime

from backend.app.deduction.schema.deduction_plan import CreateDeductionPlanParam


def test_task_schema_param_base():
    """测试推演任务配置参数"""
    container_task_config = {
        "isRoot": True,
        "isBox": True,
        "id": "185217836976229888&100861",  # fixme: container &后边的id来源是什么
        "envConfig": {"envType": "lt"},
        "bizValue": {
            "dispatchQueue": {"name": "info", "durable": True},
        },
        "pin": {"activation": None, "end": None, "delay": None, "cancel": None},
        "father": None,
    }

    agent_task_config = {
        "isRoot": True,
        "isBox": False,
        "id": "185217836976229888&10861",
        "agentLoad": "agent_lt_1",
        "envConfig": {"envType": "lt"},
        "agentUrl": "192.168.1.1:4500/scheme/agent_lt_1.zip",
        "agentConfig": {
            "ip": "192.168.1.1",
            "port": 10001,
            "side": "red",
            "deduceId": "1852178361053983008",
            "taskId": "185217836976229888&10861",
            "taskName": "本地测试智能体1",
            "unit_ids": [],
            "target_ids": [],
        },
        "bizValue": {
            "dispatchQueue": {"name": "info", "durable": True},
            "simTimeQueue": {"name": "optSimQueue", "durable": True},
        },
        "pin": {"activation": None, "end": None, "delay": None, "cancel": None},
        "agentRequire": {},
        "father": None,
    }

    deduction_plan_config = {
        "name": "测试推演方案",
        "description": "测试推演方案",
        "task_config": [container_task_config, agent_task_config],
        "start_time": datetime.now(),
    }
    deduction_plan = CreateDeductionPlanParam(**deduction_plan_config)
    print(deduction_plan.task_config[0].model_dump())
