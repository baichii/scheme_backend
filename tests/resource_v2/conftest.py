from collections.abc import AsyncIterator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.resource.api.router import v2
from backend.app.resource.service.resource_service import resource_service
from backend.common.exception.errors import BaseExceptionError
from backend.common.exception.exception_handler import base_exception_handler
from backend.common.model import MappedBase
from backend.database.db import get_db, get_db_transaction


class MemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def put(self, object_name: str, data: bytes, content_type: str) -> None:
        self.objects[object_name] = data

    async def get(self, object_name: str) -> bytes:
        return self.objects[object_name]

    async def delete(self, object_name: str) -> None:
        self.deleted.append(object_name)
        self.objects.pop(object_name, None)


@pytest_asyncio.fixture
async def resource_client() -> AsyncIterator[tuple[AsyncClient, MemoryObjectStorage]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(MappedBase.metadata.create_all)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_transaction() -> AsyncIterator[AsyncSession]:
        async with session_factory.begin() as session:
            yield session

    storage = MemoryObjectStorage()
    previous = resource_service.storage
    resource_service.storage = storage
    app = FastAPI()
    app.add_exception_handler(BaseExceptionError, base_exception_handler)
    app.include_router(v2)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_transaction] = override_transaction
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, storage
    resource_service.storage = previous
    await engine.dispose()
