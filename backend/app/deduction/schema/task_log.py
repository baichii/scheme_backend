from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import TaskLogLevel, TaskLogType
from backend.common.schema import SchemaBase


class TaskLogParamBase(SchemaBase):
    """推演任务日志参数"""

    task_id: int = Field(description="任务运行唯一ID, snowflake格式")
    suffix: int = Field(description="合成ID后缀")
    deduce_id: int = Field(description="推演方案ID, snowflake格式")
    type: TaskLogType = Field(description="消息类型")
    level: TaskLogLevel = Field(description="消息等级")
    content: str = Field(description="消息内容")


class CreateTaskLogParam(TaskLogParamBase):
    """创建推演任务日志配置参数(api传入参数)"""


class DeleteTaskLogParam(SchemaBase):
    """删除推演任务日志参数"""

    pks: list[int] = Field(description="日志记录ID列表")


class GetTaskLogDetail(TaskLogParamBase):
    """获取推演日志"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="日志记录ID")
    create_at: datetime = Field(description="创建时间")
