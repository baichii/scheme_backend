import sys

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from backend.common.log import log
from backend.common.model import MappedBase
from backend.core.conf import settings


def create_database_url(*, unittest: bool = False) -> URL:
    """
    创建数据库链接
    """

    url = URL.create(
        drivername='mysql+asyncmy' if settings.DATABASE_TYPE == 'mysql' else 'postgresql+asyncpg',
        username=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=settings.DATABASE_SCHEMA if not unittest else f'{settings.DATABASE_SCHEMA}_test',
    )
    if settings.DATABASE_TYPE == "mysql":
        url.update_query_dict({'charset': settings.DATABASE_CHARSET})
    return url


print(create_database_url())
