from typing import Any, Self
from backend.common.enums import ParamType

from pydantic import BaseModel, ConfigDict


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


class EnvTemplateParam(BaseModel):
    """环境配置模版参数"""
    name: str
    input_name: str
    type: str
    input_type: str
    required: bool
    description: str | None = None
    default_value: str | None = None
    input_type: str


