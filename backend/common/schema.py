from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.utils.timezone import timezone



class SchemaBase(BaseModel):
    """基础模型配置"""

    model_config = ConfigDict(
        use_enum_values=True,

    )