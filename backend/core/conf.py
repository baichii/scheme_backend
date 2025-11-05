from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

from backend.core.path_conf import BASE_PATH


class Settings(BaseSettings):
    """ 全局配置 """

    model_config = SettingsConfigDict(
        env_file=f"{BASE_PATH}/.env",
        env_file_encoding="utf-8",
        extra="ignore",
        cache_strings=True,
    )

    # datatime
    DATATIME_TIMEZONE: str = "Asia/Shanghai"
    DATATIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # agent
    AGENT_MINIO_HOST: str = "localhost"
    AGENT_MINIO_PORT: int = 9000
    AGENT_MINIO_USER: str = "admin"
    AGENT_MINIO_PASSWORD: str = "admin"
    AGENT_BUCKET: str = "agent"

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
