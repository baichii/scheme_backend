from pydantic import Field

from backend.common.schema import SchemaBase


class EnvInstanceParam(SchemaBase):
    """环境配置实例参数"""

    template_id: int = Field(description="环境配置模版 ID")
    name: str = Field(description="环境配置实例名称")
    params: dict = Field(description="环境配置实例参数")
