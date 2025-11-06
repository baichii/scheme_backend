from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.path_conf import BASE_PATH


class Settings(BaseSettings):
    """ 全局配置 """

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
    FASTAPI_DOCS_URL: str = '/docs'
    FASTAPI_REDOC_URL: str = '/redoc'
    FASTAPI_OPENAPI_URL: str | None = '/openapi'
    FASTAPI_STATIC_FILES: bool = False

    # datatime
    DATATIME_TIMEZONE: str = "Asia/Shanghai"
    DATATIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # fastapi

    # .env 数据库
    DATABASE_TYPE: Literal["postgresql", "mysql"]
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    # 数据库
    DATABASE_ECHO: bool | Literal["debug"] = False
    DATABASE_POOL_ECHO: bool | Literal["debug"] = False
    DATABASE_SCHEMA: str = "scheme_backend"
    DATABASE_CHARSET: str = "utf8mb4"

    # minio 用户配置
    MINIO_ENDPOINT: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    AGENT_BUCKET: str = "agent"

    # log
    LOG_STD_LEVEL: str = "INFO"
    LOG_ACCESS_FILE_LEVEL: str = 'INFO'
    LOG_ERROR_FILE_LEVEL: str = 'ERROR'
    LOG_STD_FORMAT: str = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | <lvl>{level: <8}</> | <lvl>{message}</>'
    )
    LOG_FILE_FORMAT: str = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | <lvl>{level: <8}</> | <lvl>{message}</>'
    LOG_ACCESS_FILENAME: str = 'scheme_backend_access.log'
    LOG_ERROR_FILENAME: str = 'scheme_backend_error.log'



    # # matrix rabbitmq 配置
    # MATRIX_RABBITMQ_HOST: str = "localhost"
    # MATRIX_RABBITMQ_PORT: int = 5672
    # MATRIX_RABBITMQ_USER: str = "guest"
    # MATRIX_RABBITMQ_PASSWORD: str = "guest"


@lru_cache
def get_settings() -> Settings:
    return Settings()
#
settings = get_settings()
