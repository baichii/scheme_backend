
from pydantic import BaseModel, ConfigDict


class EnvConfig(BaseModel):
    envType: str


class AgentConfig(BaseModel):
    ip: str
    port: int
    side: str
    deduceId: str
    taskId: str
    taskName: str

    model_config = ConfigDict(
        from_attributes=True,
        extra="allow"
    )


class TaskSchemeTemplate(BaseModel):
    """执行任务方案配置"""

    isRoot: bool = True
    isBox: bool = True
    id: str
    envConfig: EnvConfig
    bizValue: dict
    pin: dict
    father: str | None = None


class ContainerTaskSchemeTemplate(TaskSchemeTemplate):
    """容器任务方案配置"""


class AgentTaskSchemeTemplate(TaskSchemeTemplate):
    """智能体任务方案配置"""

    agentLoad: str | None = None
    agentUrl: str | None = None
    agentConfig: AgentConfig | None = None
    agentRequire: dict | None = {}


def test_container_task_scheme():
    test_data = {
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

    container_task_scheme = ContainerTaskSchemeTemplate(**test_data)
    assert container_task_scheme.model_dump() == test_data


def test_agent_task_scheme():
    test_data = {
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
                "target_ids": []
            },
            "bizValue": {
                "dispatchQueue": {"name": "info", "durable": True},
                "simTimeQueue": {"name": "optSimQueue", "durable": True},
            },
            "pin": {"activation": None, "end": None, "delay": None, "cancel": None},
            "agentRequire": {},
            "father": None
        }
    agent_task_scheme = AgentTaskSchemeTemplate(**test_data)
    assert agent_task_scheme.model_dump() == test_data


if __name__ == '__main__':
    test_container_task_scheme()
    test_agent_task_scheme()
