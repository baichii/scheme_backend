from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """基础模型配置"""

    model_config = ConfigDict(
        use_enum_values=True,
    )
