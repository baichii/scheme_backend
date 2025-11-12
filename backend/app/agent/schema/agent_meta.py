from datetime import datetime

from pydantic import Field, ConfigDict

from backend.common.schema import SchemaBase


class AgentSchemaBase(SchemaBase):
    """智能体元数据上传信息基础模型"""

    name: str = Field(description="智能体名称")
    description: str = Field(description="智能体描述")
    side: str | None = Field(default=None, description="智能体默认阵营")
    param_schema: dict = Field(description="智能体参数声明")
    supported_env_templates: list[int] = Field(description="支持的环境模板列表")


class CreateAgentParam(AgentSchemaBase):
    """创建智能体元数据参数(api接收参数)"""


class CreateAgentInternal(AgentSchemaBase):
    """创建智能体元数据参数(数据库存储参数)"""

    load: str = Field(description="智能体加载名称")
    url: str = Field(description="智能体文件存储路径")


class GetAgentMetaDetail(AgentSchemaBase):
    """获取智能体元数据详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="智能体 ID")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")

