from datetime import datetime
from typing import Annotated, Any

from sqlalchemy import BigInteger, DateTime, Text, TypeDecorator
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
)

from backend.core.conf import settings
from backend.utils.snowflake import snowflake
from backend.utils.timezone import timezone

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



class UniversalText(TypeDecorator[str]):
    """通用文本类型，用于存储任意文本"""
    impl = LONGTEXT if settings.DATABASE_TYPE == "mysql" else Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        return value

    def process_result_value(self, value: str | None, dialect) -> str | None:
        return value


class TimeZone(TypeDecorator[datetime]):
    """兼容性时区类型，用于存储 datetime 类型的时间"""
    impl = DateTime(timezone=True)
    cache_ok = True

    @property
    def python_type(self) -> type[datetime]:
        return datetime

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.utcoffset() != timezone.now().utcoffset():
            value = timezone.f_datetime(value)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.tz_info)
        return value


class DateTimeMixin(MappedAsDataclass):
    """日期时间 mixin数据类"""
    create_at: Mapped[datetime] = mapped_column(
        TimeZone,
        init=False,
        default_factory=timezone.now,
        sort_order=999,
        comment="创建时间"
    )
    update_at: Mapped[datetime] = mapped_column(
        TimeZone,
        init=False,
        onupdate=timezone.now,
        sort_order=999,
        comment="更新时间"
    )

class MappedBase:
    """声明式基类, 作为所有基类或数据模型的父类存在"""

    @declared_attr.directive
    def __tablename__(self) -> str:
        """生成表名"""
        return self.__name__.lower()

    @declared_attr.directive
    def __table_args__(self) -> dict[str, Any]:
        """表配置"""
        return {"comment": self.__doc__ or ""}


class DataClassBase(MappedAsDataclass, MappedBase):
    """
    声明性数据类基类, 带有数据类集成, 允许使用更高级配置, 但你必须注意它的一些特性, 尤其是和 DeclarativeBase 一起使用时

    `MappedAsDataclass <https://docs.sqlalchemy.org/en/20/orm/dataclasses.html#orm-declarative-native-dataclasses>`__
    """
    __abstract__  = True

class Base(DeclarativeBase, DateTimeMixin):
    """
    声明性数类据库模型的基类, 带有数据类集成, 并包含 MiXin 数据类基础表结构
    """

    __abstract__ = True
