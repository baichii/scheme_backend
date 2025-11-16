from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.common.enums import TaskStatus


class TaskStatusParamBase(SchemaBase):
    """推演任务状态配置参数"""
    task_id: int = Field(description="任务运行唯一ID")
    suffix: int = Field(description="合成ID后缀")
    deduce_id: int = Field(description="推演方案ID")
    status: TaskStatus = Field(description="推演任务状态")


class CreateTaskStatusParam(TaskStatusParamBase):
    """创建推演任务状态参数(api传入参数)"""


class UpdateTaskStatusParam(TaskStatusParamBase):
    """更新推演任务状态参数(api传入参数)"""


class GetTaskStatusDetail(TaskStatusParamBase):
    """获取推演任务状态详情"""
    model_config = ConfigDict(from_attributes=True)

    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")