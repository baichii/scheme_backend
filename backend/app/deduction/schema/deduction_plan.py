from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import DeductionPlanStatus
from backend.common.schema import SchemaBase


class EnvParam(SchemaBase):
    """推演方案环境配置"""
    env_type: str = Field(description="环境类型", alias="envType")


class AgentParam(SchemaBase):
    """智能体配置"""
    ip: str = Field(description="智能体IP")
    port: int = Field(description="智能体端口")
    side: str = Field(description="智能体侧")
    deduce_id: str = Field(description="推演ID", alias="deduceId")
    task_id: str = Field(description="任务ID", alias="taskId")
    task_name: str = Field(description="任务名称", alias="taskName")


class TaskSchemaParamBase(SchemaBase):
    """推演任务配置"""
    is_root: bool = Field(default=True, alias="isRoot")
    is_box: bool = Field(default=False, alias="isBox")
    id: str
    env_config: EnvParam = Field(description="推演方案环境配置", alias="envConfig")
    biz_value: dict = Field(description="业务参数", alias="bizValue")
    pin: dict = Field(description="运行配置")
    father: str | None = Field(None, description="父任务ID")


class ContainerTaskParam(TaskSchemaParamBase):
    """容器任务配置"""
    is_box: bool = Field(default=True, alias="isBox")


class AgentTaskParam(TaskSchemaParamBase):
    """智能体任务配置"""
    agent_load: str = Field(description="智能体文件名称", alias="agentLoad")
    agent_url: str = Field(description="智能体URL", alias="agentUrl")
    agent_config: AgentParam = Field(description="智能体配置", alias="agentConfig")
    agent_requires: dict = Field(default={}, description="智能体依赖")


class DeductionPlanParamBase(SchemaBase):
    """推演方案配置参数"""

    name: str = Field(description="推演方案名称")
    description: str | None = Field(None, description="推演方案描述")
    task_config: list[ContainerTaskParam | AgentTaskParam] = Field(description="推演方案配置")
    start_time: datetime | None = Field(None, description="推演开始时间")


class CreateDeductionPlanParam(DeductionPlanParamBase):
    """创建推演方案配置参数"""


class CreateDeductionPlanInternal(DeductionPlanParamBase):
    """创建推演方案配置参数(内部使用，添加默认状态)"""

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

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="推演方案ID")
    status: DeductionPlanStatus = Field(description="推演方案状态")
    env_instance_id: int | None = Field(None, description="方案运行环境实例ID")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime | None = Field(None, description="更新时间")
