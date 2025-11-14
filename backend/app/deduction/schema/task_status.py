from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.common.enums import TaskStatus


class TaskStatusParamBase(SchemaBase):
    """推演任务状态配置参数"""
    deduce_id: str = Field(description="推演方案ID")
    suffix: int = Field(description="合成ID后缀")
    status: TaskStatus = Field(description="推演任务状态")


class CreateDeductionTaskParam(TaskStatusParamBase):
    """创建推演任务配置参数(api传入参数)"""


class UpdateDeductionTaskParam(TaskStatusParamBase):
    """更新推演任务配置参数"""


class GetDeductionTaskDetail(TaskStatusParamBase):
    """获取推演任务详情"""
    model_config = ConfigDict(from_attributes=True)

    status: TaskStatus = Field(description="推演任务状态")

