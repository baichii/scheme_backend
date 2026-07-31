from functools import lru_cache

from backend.core.conf import Settings, settings
from backend.engine.client import EngineClient, EngineClientMode
from backend.engine.fake import FakeEngineClient


class EngineClientConfigurationError(RuntimeError):
    """Raised when the configured engine client cannot be created."""


def create_engine_client(config: Settings = settings) -> EngineClient:
    mode = EngineClientMode(config.ENGINE_CLIENT_MODE)
    if mode is EngineClientMode.FAKE:
        return FakeEngineClient(
            pending_seconds=config.FAKE_ENGINE_PENDING_SECONDS,
            task_duration_seconds=config.FAKE_ENGINE_TASK_DURATION_SECONDS,
            stopping_seconds=config.FAKE_ENGINE_STOPPING_SECONDS,
            log_interval_seconds=config.FAKE_ENGINE_LOG_INTERVAL_SECONDS,
            sim_time_interval_seconds=getattr(config, "FAKE_ENGINE_SIM_TIME_INTERVAL_SECONDS", 1.0),
        )
    raise EngineClientConfigurationError("ENGINE_CLIENT_MODE=matrix is not implemented")


@lru_cache(maxsize=1)
def get_engine_client() -> EngineClient:
    return create_engine_client(settings)
