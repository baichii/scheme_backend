from typing import Any, Self

from pydantic import BaseModel, ConfigDict


TypeToInputType = {
    "list": "列表",
    "str": "字符串",
    "int": "整数",
    "float": "浮点数",
    "bool": "布尔值",
}


class EnvTemplateParam(BaseModel):
    """环境配置模版参数"""
    name: str
    input_name: str
    type: str
    required: bool
    description: str | None = None
    default_value: str | None = None
    input_type: str | None = None

