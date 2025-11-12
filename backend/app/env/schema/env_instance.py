from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class EnvInstanceParamBase(SchemaBase):
    """环境配置实例参数"""

    template_id: int = Field(description="环境配置模版 ID")
    name: str = Field(description="环境配置实例名称")
    params: dict = Field(description="环境配置实例参数")


class CreateEnvInstanceParam(EnvInstanceParamBase):
    """创建环境配置实例参数"""


class UpdateEnvInstanceParam(EnvInstanceParamBase):
    """更新环境配置实例参数"""


class GetEnvInstanceDetail(EnvInstanceParamBase):
    """环境配置实例详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="实例ID")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")
