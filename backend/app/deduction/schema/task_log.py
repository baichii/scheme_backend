from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.common.model import snowflake_id_key
from backend.common.enums import TaskLogType, TaskLogLevel


class TaskLogParamBase(SchemaBase):
    """推演任务日志参数"""
    type: TaskLogType = Field(description="消息类型")
    level: TaskLogLevel = Field(description="消息等级")
    content: str = Field(description="消息内容")


class CreateTaskLogParam(TaskLogParamBase):
    """创建推演任务日志配置参数(api传入参数)"""
    task_id: snowflake_id_key = Field(description="任务运行唯一ID")
    suffix: int = Field(description="合成ID后缀")


class GetTaskLogDetail(TaskLogParamBase):
    """获取推演日志"""
    id: int = Field(description="日志记录ID")
    task_id: snowflake_id_key = Field(description="任务运行唯一ID")
    suffix: int = Field(description="合成ID后缀")
    create_at: datetime = Field(description="创建时间")

