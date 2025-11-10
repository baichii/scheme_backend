from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class EnvTemplateParamBase(SchemaBase):
    """环境配置模版参数"""

    name: str = Field(description="环境配置模版名称")
    param_schema: dict = Field(description="环境配置模版参数 schema")


class CreateEnvTemplateParam(EnvTemplateParamBase):
    """创建环境配置模版参数"""


class GetEnvTemplateDetail(EnvTemplateParamBase):
    """环境配置模版详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="模版ID")
    name: str = Field(description="环境配置模版名称")
    param_schema: dict = Field(description="环境配置模版参数 schema")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")
