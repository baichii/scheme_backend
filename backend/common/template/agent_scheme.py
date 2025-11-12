from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


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


class AgentSchemeTemplate(BaseModel):
    """智能体方案配置"""

    isRoot: bool = True
    isBox: bool = True
    id: str
    agentLoad: str
    agentUrl: str
    envConfig: EnvConfig
    agentConfig: AgentConfig
    bizValue: dict
    pin: dict
    pinTime: dict | None = None
    agentRequire: dict | None = {}
    activation: dict | None = None
    father: str | None = None


def test_agent_scheme():
    test_data = {
                "isRoot": True,
                "isBox": True,
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
                    "deduceID": "1852178361053983008",
                    "deduceTaskID": "185217836976229888&10861"
                },
                "pin": {"activation": None, "end": None, "delay": None, "cancel": None},
                "pinTime": None,
                "agentRequire": {},
                "activation": None,
                "father": None
            }
    agent_scheme = AgentSchemeTemplate(**test_data)
    assert agent_scheme.model_dump() == test_data


if __name__ == '__main__':
    test_agent_scheme()
