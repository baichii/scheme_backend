from types import SimpleNamespace

import pytest

from backend.engine.client import EngineClient, EngineClientMode
from backend.engine.fake import FakeEngineClient
from backend.engine.provider import (
    EngineClientConfigurationError,
    create_engine_client,
    get_engine_client,
)


def make_settings(mode: str):
    return SimpleNamespace(
        ENGINE_CLIENT_MODE=mode,
        FAKE_ENGINE_PENDING_SECONDS=0.01,
        FAKE_ENGINE_TASK_DURATION_SECONDS=0.02,
        FAKE_ENGINE_STOPPING_SECONDS=0.01,
        FAKE_ENGINE_LOG_INTERVAL_SECONDS=0.005,
    )


@pytest.mark.asyncio
async def test_provider_builds_fake_engine_client():
    client = create_engine_client(make_settings("fake"))
    try:
        assert isinstance(client, FakeEngineClient)
        assert isinstance(client, EngineClient)
        assert client.mode is EngineClientMode.FAKE
    finally:
        await client.aclose()


def test_provider_does_not_fall_back_when_matrix_is_unimplemented():
    with pytest.raises(EngineClientConfigurationError, match="not implemented"):
        create_engine_client(make_settings("matrix"))


@pytest.mark.asyncio
async def test_default_provider_is_process_singleton():
    get_engine_client.cache_clear()
    first = get_engine_client()
    second = get_engine_client()
    try:
        assert first is second
    finally:
        await first.aclose()
        get_engine_client.cache_clear()
