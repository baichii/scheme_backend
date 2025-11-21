from typing import Any

from pydantic import BaseModel, ConfigDict
from backend.common.enums import ParamType


class SchemaBase(BaseModel):
    """基础模型配置"""

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        alias_generator=None,
        serialize_by_alias=True,
        extra="allow",
    )


TypeToInputType = {
    ParamType.LIST: "列表",
    ParamType.STR: "字符串",
    ParamType.INT: "整数",
    ParamType.FLOAT: "浮点数",
    ParamType.BOOL: "布尔值",
    ParamType.DATETIME: "日期时间",
    ParamType.TABLE: "表格",
    ParamType.INDEX: "代字索引",
    ParamType.ENUM: "枚举",
    ParamType.ENUM_MULTI: "多选枚举",
    ParamType.AREA: "区域",
    ParamType.NAMED_AREA: "命名区域",
    ParamType.ROUTE: "路径",
}


class ParamDeclarationSchema(SchemaBase):
    """参数声明配置"""
    name: str
    type: str
    input_type: str
    required: bool
    description: str | None = None
    default_value: Any | None = None
    other: dict | None = None  # other字段用于处理表格类型/枚举等类型额外字段

    # todo: 自动生成类型, 暂不确定输入是type还是input_type
