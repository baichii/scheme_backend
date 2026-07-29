import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def cleanup_templates():
    """Keep engine unit tests independent from the API server fixture."""
    yield
