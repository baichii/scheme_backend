from enum import Enum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from backend.common.enums import EngineRequestType


class EngineProtocolModel(BaseModel):
    """Base model for the Matrix-compatible engine protocol."""

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        extra="allow",
    )


class EngineTaskState(str, Enum):
    UNKNOWN = "-1"
    READY = "0"
    PENDING = "1"
    RUNNING = "2"
    STOPPING = "3"
    END = "4"
    ERROR = "5"


class EngineQueueConfig(EngineProtocolModel):
    name: str = ""
    durable: bool = True
    need_to_declare: bool = Field(default=True, alias="needToDeclare")


class EngineStopDispatchQueue(EngineProtocolModel):
    name: str = "info"
    durable: bool = True


class EngineEnvironmentConfig(EngineProtocolModel):
    env_type: str = Field(default="", alias="envType")
    env_instance_config: dict[str, Any] = Field(default_factory=dict, alias="envInstanceConfig")


class EngineAgentConfig(EngineProtocolModel):
    deduce_id: str | None = Field(default=None, alias="deduceId")
    task_id: str | None = Field(default=None, alias="taskId")
    task_name: str = Field(default="", alias="taskName")
    agent_instance_config: dict[str, Any] = Field(default_factory=dict, alias="agentInstanceConfig")


class EngineBizValue(EngineProtocolModel):
    dispatch_queue: EngineQueueConfig = Field(default_factory=EngineQueueConfig, alias="dispatchQueue")
    sim_time_queue: EngineQueueConfig = Field(default_factory=EngineQueueConfig, alias="simTimeQueue")
    deduce_id: str | None = Field(default=None, alias="deduceID")
    deduce_task_id: str | None = Field(default=None, alias="deduceTaskID")


class EnginePinConfig(EngineProtocolModel):
    activate: str | None = None
    end: str | None = None
    delay: str | None = None
    cancel: str | None = None


class EngineTaskDefinition(EngineProtocolModel):
    is_root: bool = Field(default=True, alias="isRoot")
    is_box: bool = Field(default=False, alias="isBox")
    id: str = Field(min_length=1)
    env_config: EngineEnvironmentConfig = Field(default_factory=EngineEnvironmentConfig, alias="envConfig")
    agent_load: str = Field(default="", alias="agentLoad")
    agent_url: str = Field(default="", alias="agentUrl")
    agent_config: EngineAgentConfig = Field(default_factory=EngineAgentConfig, alias="agentConfig")
    biz_value: EngineBizValue = Field(default_factory=EngineBizValue, alias="bizValue")
    pin: EnginePinConfig = Field(default_factory=EnginePinConfig)
    agent_require: dict[str, Any] = Field(default_factory=dict, alias="agentRequire")
    father: str | None = None


class EngineCreateRequest(EngineProtocolModel):
    name: str = "create"
    request_type: Literal[1] = Field(default=EngineRequestType.CREATE.value, alias="requestType")
    body: list[EngineTaskDefinition] = Field(default_factory=list)


class EngineQueryRequest(EngineProtocolModel):
    name: str = "query"
    request_type: Literal[3] = Field(default=EngineRequestType.QUERY.value, alias="requestType")
    body: list[str] = Field(default_factory=list)


class EngineStopRequest(EngineProtocolModel):
    name: str = "stop"
    request_type: Literal[4] = Field(default=EngineRequestType.STOP.value, alias="requestType")
    body: list[str] = Field(default_factory=list)
    dispatch_queue: EngineStopDispatchQueue = Field(
        default_factory=EngineStopDispatchQueue,
        alias="dispatchQueue",
    )


ResponseDataT = TypeVar("ResponseDataT")


class EngineResponse(EngineProtocolModel, Generic[ResponseDataT]):
    code: int
    data: ResponseDataT
    error_info: str = ""


class EngineStateChange(EngineProtocolModel):
    id: str
    now: EngineTaskState


class EngineStateDispatchMessage(EngineProtocolModel):
    message_type: Literal["state"] = Field(default="state", alias="messageType")
    biz_value: EngineBizValue = Field(alias="bizValue")
    message: EngineStateChange


class EngineLogDispatchMessage(EngineProtocolModel):
    message_type: Literal["log"] = Field(default="log", alias="messageType")
    biz_value: EngineBizValue = Field(alias="bizValue")
    level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    message: str


EngineDispatchMessage = EngineStateDispatchMessage | EngineLogDispatchMessage


class EngineEventRecord(EngineProtocolModel):
    sequence: int = Field(gt=0)
    task_id: str
    payload: EngineDispatchMessage
