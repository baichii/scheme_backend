from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.common.enums import DeductionPlanStatus


class DeductionPlanParamBase(SchemaBase):
    """推演方案配置参数"""

    name: str = Field(description="推演方案名称")
    description: str | None = Field(None, description="推演方案描述")
    task_config: list[dict] = Field(description="推演方案配置")
    start_time: datetime | None = Field(None, description="推演开始时间")


class CreateDeductionPlanParam(DeductionPlanParamBase):
    """创建推演方案配置参数(api传入参数)"""


class CreateDeductionPlanInternal(DeductionPlanParamBase):
    """创建推演方案配置参数(上传数据库)"""
    id: int = Field(description="推演方案ID")
    status: DeductionPlanStatus = Field(description="推演方案状态")


class UpdateDeductionPlanParam(DeductionPlanParamBase):
    """更新推演方案配置参数"""


class ExecuteDeductionPlanParam(SchemaBase):
    """执行推演方案参数"""
    env_instance_id: int = Field(description="环境实例ID")


class DeleteDeductionPlanParam(SchemaBase):
    pks: list[int] = Field(description="推演方案ID列表")


class GetDeductionPlanParam(DeductionPlanParamBase):
    """获取推演方案配置参数"""

    id: int = Field(description="推演方案ID")
    status: DeductionPlanStatus = Field(description="推演方案状态")
    env_instance_id: int | None = Field(None, description="方案运行环境实例ID")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")
