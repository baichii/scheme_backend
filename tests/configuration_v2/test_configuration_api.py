from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.app.configuration.api.router import v2
from backend.app.configuration.service.configuration_service import (
    CONFIGURATION_PATH,
    ConfigurationService,
)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    app.include_router(v2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest.mark.asyncio
async def test_configuration_lists_match_frontend_contract(client: AsyncClient) -> None:
    templates = (await client.get("/api/v2/configuration/environment-templates")).json()
    scenarios = (await client.get("/api/v2/configuration/scenario-types")).json()

    assert [item["key"] for item in templates] == ["local_test", "pysim"]
    zc3 = next(item for item in scenarios if item["key"] == "zc3")
    assert zc3["defaultSideKey"] == "red"
    assert zc3["sides"] == [{"key": "red", "name": "红方"}, {"key": "blue", "name": "蓝方"}]


@pytest.mark.asyncio
async def test_frontend_configuration_routes_are_not_registered(client: AsyncClient) -> None:
    assert (await client.get("/api/v2/configuration/toolbox-items")).status_code == 404
    assert (await client.get("/api/v2/configuration/assets/flags/china.svg")).status_code == 404


def test_loader_rejects_unknown_scenario_template(tmp_path: Path) -> None:
    target = tmp_path / "config"
    _copy_configuration(CONFIGURATION_PATH, target)
    scenario = target / "scenario_types" / "zc3.yaml"
    scenario.write_text(scenario.read_text().replace("  - pysim", "  - missing"), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown templates"):
        ConfigurationService(target)


def test_loader_rejects_frontend_presentation_fields(tmp_path: Path) -> None:
    target = tmp_path / "config"
    _copy_configuration(CONFIGURATION_PATH, target)
    scenario = target / "scenario_types" / "zc3.yaml"
    scenario.write_text(
        scenario.read_text().replace("    name: 红方", "    name: 红方\n    flag: china.svg"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        ConfigurationService(target)


def test_loader_rejects_duplicate_yaml_keys_and_unregistered_scenarios(tmp_path: Path) -> None:
    target = tmp_path / "duplicate"
    _copy_configuration(CONFIGURATION_PATH, target)
    index = target / "index.yaml"
    index.write_text(f"{index.read_text()}\nscenario_types: [zc3]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate YAML key"):
        ConfigurationService(target)

    target = tmp_path / "unregistered"
    _copy_configuration(CONFIGURATION_PATH, target)
    scenario = target / "scenario_types" / "extra.yaml"
    scenario.write_text(
        (target / "scenario_types" / "zc3.yaml").read_text().replace("key: zc3", "key: extra"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="scenario type catalog"):
        ConfigurationService(target)


def _copy_configuration(source: Path, target: Path) -> None:
    import shutil

    shutil.copytree(source, target)
