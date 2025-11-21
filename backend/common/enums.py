from enum import Enum, IntEnum as SourceIntEnum
from typing import Any, TypeVar


T = TypeVar("T", bound=Enum)


class _EnumBase:
    """枚举基类, 提供通用方法"""

    @classmethod
    def get_member_key(cls) -> list[str]:
        return list(cls.__members__.keys())

    @classmethod
    def get_member_value(cls) -> list[Any]:
        return [item.value for item in cls.__members__.values()]

    @classmethod
    def get_member_dict(cls) -> dict[str, Any]:
        return {key: item.value for key, item in cls.__members__.items()}


class IntEnum(_EnumBase, SourceIntEnum):
    """整数枚举基类"""


class StrEnum(_EnumBase, Enum):
    """字符串枚举基类"""


class DeductionPlanStatus(StrEnum):
    """推演方案状态枚举"""

    INACTIVE = "inactive"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class TaskStatus(StrEnum):
    """推演任务状态枚举"""

    UNKNOWN = "unknown"
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    TERMINAL = "terminal"


class TaskLogType(StrEnum):
    """推演任务消息类型枚举"""

    LOG = "log"
    EVENT = "event"
    ECHART = "echart"


class TaskLogLevel(StrEnum):
    """推演任务消息等级枚举"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EngineRequestType(IntEnum):
    """engine请求类型"""

    CREATE = 1
    UPDATE = 2
    QUERY = 3
    STOP = 4


class ParamType:
    """参数类型枚举"""

    LIST = "list"
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    TABLE = "table"
    INDEX = "index"
    ENUM = "enum"
    ENUM_MULTI = "enum_multi"
    AREA = "area"
    NAMED_AREA = "named_area"
    ROUTE = "route"
