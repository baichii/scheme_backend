from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.path_conf import BASE_PATH


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=f"{BASE_PATH}/.env",
        env_file_encoding="utf-8",
        extra="ignore",
        cache_strings=True,
    )

    # env
    ENVIRONMENT: Literal["dev", "prod"] = "dev"

    # fastapi
    FAST_API_V1_PATH: str = "/api/v1"
    FASTAPI_TITLE: str = "Scheme Backend"
    FASTAPI_VERSION: str = "0.0.1"
    FASTAPI_DESCRIPTION: str = "Scheme Backend By FastAPI"
    FASTAPI_DOCS_URL: str = "/docs"
    FASTAPI_REDOC_URL: str = "/redoc"
    FASTAPI_OPENAPI_URL: str | None = "/openapi"
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://127.0.0.1:4173",
        "http://127.0.0.1:4174",
        "http://localhost:4173",
        "http://localhost:4174",
    ]

    # datetime
    DATETIME_TIMEZONE: str = "Asia/Shanghai"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # fastapi

    # .env 数据库
    DATABASE_TYPE: Literal["postgresql", "mysql", "sqlite"]
    DATABASE_HOST: str = "127.0.0.1"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = ""
    DATABASE_PASSWORD: str = ""

    # 数据库
    DATABASE_ECHO: bool | Literal["debug"] = False
    DATABASE_POOL_ECHO: bool | Literal["debug"] = False
    DATABASE_SCHEMA: str = "scheme_backend"
    DATABASE_CHARSET: str = "utf8mb4"
    DATABASE_SQLITE_PATH: str = "local_dev.db"

    # minio 用户配置
    MINIO_ENDPOINT: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    RESOURCE_BUCKET: str = "scheme-resources"

    # log
    LOG_STD_LEVEL: str = "INFO"
    LOG_ACCESS_FILE_LEVEL: str = "INFO"
    LOG_ERROR_FILE_LEVEL: str = "ERROR"
    LOG_STD_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | <lvl>{level: <8}</> | <lvl>{message}</>"
    )
    LOG_FILE_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | <lvl>{level: <8}</> | <lvl>{message}</>"
    )
    LOG_ACCESS_FILENAME: str = "scheme_backend_access.log"
    LOG_ERROR_FILENAME: str = "scheme_backend_error.log"

    # engine配置
    ENGINE_CLIENT_MODE: Literal["fake", "matrix"] = "fake"
    ENGINE_ENDPOINT: str
    ENGINE_RABBITMQ_HOST: str
    ENGINE_RABBITMQ_PORT: int
    ENGINE_RABBITMQ_USER: str
    ENGINE_RABBITMQ_PASSWORD: str
    ENGINE_RABBITMQ_QUEUE_NAME: str
    FAKE_ENGINE_PENDING_SECONDS: float = 0.1
    FAKE_ENGINE_TASK_DURATION_SECONDS: float = 10.0
    FAKE_ENGINE_STOPPING_SECONDS: float = 0.1
    FAKE_ENGINE_LOG_INTERVAL_SECONDS: float = 1.0
    FAKE_ENGINE_SIM_TIME_INTERVAL_SECONDS: float = 1.0
    ENGINE_EVENT_POLL_INTERVAL_SECONDS: float = 0.05
    RUNTIME_SSE_HEARTBEAT_SECONDS: float = 15.0

    # engine api路由
    ENGINE_CREATE: str = "/api/create"
    ENGINE_UPDATE: str = "/api/update"
    ENGINE_QUERY: str = "/api/query"
    ENGINE_STOP: str = "/api/stop"
    ENGINE_HEALTH_CHECK: str = "/api/health_check"


@lru_cache
def get_settings() -> Settings:
    return Settings()


#
settings = get_settings()
