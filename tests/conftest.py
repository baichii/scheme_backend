"""
Test configuration file - Provides common fixtures
Uses real HTTP requests to avoid async event loop issues
"""

import pytest_asyncio
import httpx


@pytest_asyncio.fixture
async def client():
    """Async HTTP client that connects to the real running server"""
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def cleanup_templates(client):
    """Auto cleanup all templates after each test"""
    yield
    # Cleanup after test: get all templates and delete them one by one
    try:
        response = await client.get("/api/v1/env/template/all")
        if response.status_code == 200:
            templates = response.json().get("data", [])
            for template in templates:
                await client.delete(f"/api/v1/env/template/{template['id']}")
    except Exception:
        pass  # Ignore cleanup errors


def sample_env_template_factory():
    """Factory function to create unique template data"""
    import time
    unique_suffix = str(int(time.time() * 1000000))  # microseconds for uniqueness
    return {
        "name": f"Test Template {unique_suffix}",
        "param_schema": [
            {
                "name": "ip",
                "type": "str",
                "input_type": "string",
                "required": True,
                "description": "IP address of environment",
                "default_value": None,
            },
            {
                "name": "port",
                "type": "int",
                "input_type": "integer",
                "required": True,
                "description": "Service port",
                "default_value": None,
            },
        ],
    }


@pytest_asyncio.fixture
def sample_env_template():
    """Standard test template data with unique name"""
    return sample_env_template_factory()
