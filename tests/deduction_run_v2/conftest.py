from collections.abc import AsyncIterator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.branch_scheme.model.branch_scheme import BranchScheme, BranchSchemeRevision
from backend.app.branch_scheme.schema.branch_scheme import get_default_branch_scheme_graph
from backend.app.deduction.api.router import v2 as deduction_v2
from backend.app.deduction.model.deduction import Deduction
from backend.app.deduction_run.api.router import v2 as deduction_run_v2
from backend.app.deduction_run.service.coordinator import DeductionRunCoordinator
from backend.app.resource.model.resource import Resource, ResourceVersion
from backend.common.exception.errors import BaseExceptionError
from backend.common.exception.exception_handler import base_exception_handler
from backend.common.model import MappedBase
from backend.database.db import get_db, get_db_transaction
from backend.engine.fake import FakeEngineClient


def _configured_branch_graph(agent_id: int, version_id: int) -> dict:
    graph = get_default_branch_scheme_graph().model_dump(mode="json", by_alias=True)
    for node in graph["nodes"]:
        if node["scope"] == "task":
            node["agentBinding"] = {
                "resourceId": str(agent_id),
                "resourceName": "Runtime 测试智能体",
                "agentVersionId": str(version_id),
                "agentRevisionNumber": 1,
                "parameters": {"threshold": 0.75},
            }
    return graph


@pytest_asyncio.fixture
async def runtime_client(tmp_path) -> AsyncIterator[tuple[AsyncClient, async_sessionmaker, int, object]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(MappedBase.metadata.create_all)

    agent_id = 10000
    agent_version_id = 5001
    environment_id = 6001
    branch_values = ((2001, 3001, "红方方案"), (2002, 3002, "蓝方方案"))
    async with session_factory.begin() as session:
        session.add(
            Resource(
                id=agent_id,
                type="agent",
                name="Runtime 测试智能体",
                normalized_name="runtime 测试智能体",
                current_version_id=agent_version_id,
            )
        )
        session.add(
            ResourceVersion(
                id=agent_version_id,
                resource_id=agent_id,
                version="R1",
                revision_number=1,
                package_version="0.1.0",
                format="ZIP",
                file_name="runtime_agent.zip",
                size=100,
                checksum="a" * 64,
                object_key="resources/10000/versions/5001/runtime_agent.zip",
                parsed_data={"PARAMS": [], "STATUS": ["运行中"], "VERSION": "0.1.0"},
                validation={"status": "valid", "issues": [], "summary": {}},
            )
        )
        session.add(
            Resource(
                id=environment_id,
                type="environment",
                name="Runtime 测试环境",
                normalized_name="runtime 测试环境",
                current_version_id=None,
                environment={
                    "template": "local_test",
                    "scenarioTypeKey": "local_test",
                    "values": {"ip": "127.0.0.1", "port": 10002},
                },
            )
        )
        graph = _configured_branch_graph(agent_id, agent_version_id)
        for branch_id, revision_id, name in branch_values:
            session.add(
                BranchScheme(
                    id=branch_id,
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
                    branch_scheme_id=branch_id,
                    revision_number=1,
                    name=name,
                    description="Runtime 固定修订",
                    scenario_type_key="local_test",
                    side_key="red",
                    status="configured",
                    graph=graph,
                    created_by="当前用户",
                )
            )
        deduction = Deduction(
            name="Runtime 联调推演",
            normalized_name="runtime 联调推演",
            scenario_type_key="local_test",
            status="ready",
            graph={
                "nodes": [
                    {"id": "start", "kind": "start", "name": "开始", "position": {"x": 0, "y": 0}},
                    {
                        "id": "branch-red",
                        "kind": "branch-scheme",
                        "branchSchemeId": "2001",
                        "branchSchemeName": "红方方案",
                        "branchSchemeRevisionId": "3001",
                        "revisionNumber": 1,
                        "position": {"x": 200, "y": 0},
                    },
                    {
                        "id": "branch-blue",
                        "kind": "branch-scheme",
                        "branchSchemeId": "2002",
                        "branchSchemeName": "蓝方方案",
                        "branchSchemeRevisionId": "3002",
                        "revisionNumber": 1,
                        "position": {"x": 400, "y": 0},
                    },
                    {"id": "end", "kind": "end", "name": "结束", "position": {"x": 600, "y": 0}},
                ],
                "edges": [
                    {"id": "e1", "source": "start", "target": "branch-red"},
                    {"id": "e2", "source": "branch-red", "target": "branch-blue"},
                    {"id": "e3", "source": "branch-blue", "target": "end"},
                ],
            },
        )
        session.add(deduction)
        await session.flush()
        deduction_id = deduction.id

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_transaction() -> AsyncIterator[AsyncSession]:
        async with session_factory.begin() as session:
            yield session

    fake = FakeEngineClient(
        pending_seconds=0.005,
        task_duration_seconds=0.04,
        stopping_seconds=0.005,
        log_interval_seconds=0.005,
        sim_time_interval_seconds=0.005,
    )
    coordinator = DeductionRunCoordinator(
        session_factory=session_factory,
        engine=fake,
        poll_interval=0.001,
        heartbeat_seconds=0.02,
    )
    app = FastAPI()
    app.add_exception_handler(BaseExceptionError, base_exception_handler)
    app.include_router(deduction_v2)
    app.include_router(deduction_run_v2)
    app.state.deduction_run_coordinator = coordinator
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_transaction] = override_transaction
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_factory, deduction_id, coordinator
    await coordinator.aclose()
    await engine.dispose()
