from datetime import datetime

from pydantic import Field, ConfigDict

from backend.common.schema import SchemaBase


class SchemeParamBase(SchemaBase):
    """方案参数"""

    name: str = Field(description="方案实例名称")
    description: str = Field(description="方案实例描述")
    side: str = Field(description="方案所属阵营")
    config: dict = Field(description="方案配置")


class CreateSchemeParam(SchemeParamBase):
    """创建方案参数"""


class UpdateSchemeParam(SchemeParamBase):
    """更新方案参数"""
    config: dict = Field(description="方案配置")


class GetSchemeDetail(SchemeParamBase):
    """方案详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="方案ID")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")
