from collections.abc import AsyncIterator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.branch_scheme.model.branch_scheme import BranchScheme, BranchSchemeRevision
from backend.app.branch_scheme.schema.branch_scheme import get_default_branch_scheme_graph
from backend.app.deduction.api.router import v2
from backend.common.exception.errors import BaseExceptionError
from backend.common.exception.exception_handler import base_exception_handler
from backend.common.model import MappedBase
from backend.database.db import get_db, get_db_transaction


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(MappedBase.metadata.create_all)
    async with session_factory.begin() as session:
        graph = get_default_branch_scheme_graph().model_dump(mode="json", by_alias=True)
        for scheme_id, revision_id, name in (
            (101, 1001, "方案 101"),
            (102, 1002, "方案 102"),
        ):
            session.add(
                BranchScheme(
                    id=scheme_id,
                    normalized_name=name.casefold(),
                    head_revision_id=revision_id,
                    head_revision_number=1,
                    created_by="当前用户",
                    published_revision_id=revision_id,
                    published_revision_number=1,
                )
            )
            session.add(
                BranchSchemeRevision(
                    id=revision_id,
                    branch_scheme_id=scheme_id,
                    revision_number=1,
                    name=name,
                    description="Deduction 测试固定修订",
                    scenario_type_key="zc",
                    side_key="red",
                    status="configured",
                    graph=graph,
                    created_by="当前用户",
                )
            )

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_transaction() -> AsyncIterator[AsyncSession]:
        async with session_factory.begin() as session:
            yield session

    app = FastAPI()
    app.add_exception_handler(BaseExceptionError, base_exception_handler)
    app.include_router(v2)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_transaction] = override_transaction

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client

    await engine.dispose()
