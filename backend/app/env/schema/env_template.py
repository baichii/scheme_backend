from pydantic import Field

from backend.common.schema import SchemaBase


class EnvTemplateParam(SchemaBase):
    """环境配置模版参数"""

    name: str = Field(description="环境配置模版名称")
    param_schema: dict = Field(description="环境配置模版参数 schema")
