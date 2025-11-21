from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """基础模型配置"""

    model_config = ConfigDict(
        use_enum_values=True,
    )



TypeToInputType = {
    "list": "列表",
    "str": "字符串",
    "int": "整数",
    "float": "浮点数",
    "bool": "布尔值",
}


class ParamSchema(SchemaBase):
    """参数模型配置"""
    name: str
    type: str
    required: bool
    description: str | None = None
    default_value: any | None = None
    other: dict | None = None


