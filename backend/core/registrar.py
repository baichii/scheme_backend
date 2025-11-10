from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from backend.app.router import route
from backend.common.log import set_custom_logfile, setup_logging
from backend.core.conf import settings
from backend.database.db import create_tables
from backend.utils.health_check import ensure_unique_route_names
from backend.utils.openapi import simplify_operation_ids


@asynccontextmanager
async def register_init(app: FastAPI):
    """
    启动初始化
    """

    # 创建数据库 & 连接db
    await create_tables()
    yield


def register_app() -> FastAPI:
    """注册FastAPI应用"""

    app = FastAPI(
        title=settings.FASTAPI_TITLE,
        version=settings.FASTAPI_VERSION,
        description=settings.FASTAPI_DESCRIPTION,
        docs_url=settings.FASTAPI_DOCS_URL,
        redoc_url=settings.FASTAPI_REDOC_URL,
        openapi_url=settings.FASTAPI_OPENAPI_URL,
        static_files=settings.FASTAPI_STATIC_FILES,
        lifespan=register_init,
    )

    # 注册组件
    register_logger()
    register_router(app)
    register_page(app)

    return app


def register_logger() -> None:
    """
    系统日志
    """
    setup_logging()
    set_custom_logfile()


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
