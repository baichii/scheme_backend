from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase


class AgentMetaSchemeBase(SchemaBase):

    agent_id: int = Field(description="智能体唯一id")
    agent_name: str = Field(description="智能体名称")
    agent_load: str = Field(description="智能体文件加载名称")
    agent_desc: str = Field(description="智能体描述")
    agent_url: str = Field(description="智能体下载路径")
    side: str | int = Field(description="智能体默认阵营")
    param_schema: dict = Field(description="智能体参数声明")
    supported_env_templates: list[str] = Field(description="支持的环境模板列表")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime = Field(description="更新时间")



