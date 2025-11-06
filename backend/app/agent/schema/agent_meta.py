from pydantic import Field

from backend.common.schema import SchemaBase


class AgentUploadRequest(SchemaBase):
    """智能体上传请求 Schema"""

    agent_name: str = Field(description="智能体名称")
    agent_load: str = Field(description="智能体文件加载名称, 不含文件后缀")
    agent_desc: str = Field(description="智能体描述")
    side: str | None = Field(default=None, description="智能体默认阵营")
    params_schema: dict = Field(description="智能体参数声明")
    supported_env_templates: list[int] = Field(description="支持的环境模板列表")
    agent_file: str = Field(description="智能体文件名")


class AgentCreateRequest(SchemaBase):
    """创建智能体请求 Schema"""

    agent_name: str = Field(description="智能体名称")
    agent_load: str = Field(description="智能体文件加载名称, 不含文件后缀")
    agent_desc: str = Field(description="智能体描述")
    agent_url: str = Field(description="智能体下载路径")
    side: str = Field(description="智能体默认阵营")
    param_schema: dict = Field(description="智能体参数声明")
    supported_env_templates: list[str] = Field(description="支持的环境模板列表")




