from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.common.enums import DeductionStatus


class DeductionPlanParamBase(SchemaBase):
    """推演方案配置参数"""

    name: str = Field(description="推演方案名称")
    description: str | None = Field(None, description="推演方案描述")
    plan_config: dict = Field(description="推演方案配置")
    start_time: datetime | None = Field(None, description="推演开始时间")


class CreateDeductionPlanParam(DeductionPlanParamBase):
    """创建推演方案配置参数(api传入参数)"""


class CreateDeductionPlanInternal(DeductionPlanParamBase):
    """创建推演方案配置参数(上传数据库)"""
    plan_id: int = Field(description="推演方案ID")
    status: DeductionStatus = Field(description="推演方案状态")



class UpdateDeductionPlanParam(DeductionPlanParamBase):
    """更新推演方案配置参数"""
    id: int = Field(description="推演方案ID")
    plan_config: dict = Field(description="推演方案配置")


class GetDeductionPlanParam(SchemaBase):
    """获取推演方案配置参数"""

    id: int = Field(description="推演方案ID")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")
