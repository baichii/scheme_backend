from datetime import datetime
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, Text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, mapped_column

from backend.utils.snowflake import snowflake

# 通用Mapped 类型主键, 需要手动添加
id_key = Annotated[
    int,
    mapped_column(
        BigInteger,
        primary_key=True,
        unique=True,
        index=True,
        autoincrement=True,
        sort_order=-999,
        comment="主键ID"
    )
]


# 雪花算法 Mapped 类型主键，使用方法与 id_key 相同
# 详情：https://fastapi-practices.github.io/fastapi_best_architecture_docs/backend/reference/pk.html
snowflake_id_key = Annotated[
    int,
    mapped_column(
        BigInteger,
        primary_key=True,
        unique=True,
        index=True,
        default=snowflake.generate,
        sort_order=-999,
        comment='雪花算法主键 ID',
    ),
]


# 数据库模型基类
class Base(DeclarativeBase):
    """所有数据库模型的基类"""
    pass
