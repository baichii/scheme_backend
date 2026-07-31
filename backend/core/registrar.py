from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from backend.app.deduction_run.service.coordinator import create_deduction_run_coordinator
from backend.app.router import route
from backend.common.exception.errors import BaseExceptionError
from backend.common.exception.exception_handler import base_exception_handler
from backend.common.log import set_custom_logfile, setup_logging
from backend.core.conf import settings
from backend.database.db import create_tables
from backend.engine.provider import get_engine_client
from backend.utils.health_check import ensure_unique_route_names
from backend.utils.openapi import simplify_operation_ids


@asynccontextmanager
async def register_init(app: FastAPI):
    """
    启动初始化
    """

    # 创建数据库 & 连接db
    await create_tables()
    coordinator = create_deduction_run_coordinator()
    app.state.deduction_run_coordinator = coordinator
    await coordinator.reconcile()
    try:
        yield
    finally:
        await coordinator.aclose()
        get_engine_client.cache_clear()


def register_app() -> FastAPI:
    """注册FastAPI应用"""

    app = FastAPI(
        title=settings.FASTAPI_TITLE,
        version=settings.FASTAPI_VERSION,
        description=settings.FASTAPI_DESCRIPTION,
        docs_url=settings.FASTAPI_DOCS_URL,
        redoc_url=settings.FASTAPI_REDOC_URL,
        openapi_url=settings.FASTAPI_OPENAPI_URL,
        lifespan=register_init,
    )

    # 注册组件
    register_logger()
    register_exception(app)
    register_cors(app)
    register_router(app)
    register_page(app)

    return app


def register_logger() -> None:
    """
    系统日志
    """
    setup_logging()
    set_custom_logfile()


def register_exception(app: FastAPI) -> None:
    """注册业务异常处理器。"""
    app.add_exception_handler(BaseExceptionError, base_exception_handler)


def register_cors(app: FastAPI) -> None:
    """注册前端联调跨域配置。"""

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_router(app: FastAPI):
    """
    注册路由
    """
    dependencies = None
    app.include_router(route, dependencies=dependencies)

    ensure_unique_route_names(app)
    simplify_operation_ids(app)


def register_page(app: FastAPI) -> None:
    """
    注册分页组件
    """
    add_pagination(app)
