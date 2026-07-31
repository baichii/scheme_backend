from fastapi import APIRouter

from backend.app.configuration.schema.configuration import (
    GetEnvironmentTemplate,
    GetScenarioType,
)
from backend.app.configuration.service.configuration_service import configuration_service

router = APIRouter(prefix="/configuration", tags=["产品配置 V2"])


@router.get("/environment-templates", response_model=list[GetEnvironmentTemplate])
async def get_environment_template_list() -> list[GetEnvironmentTemplate]:
    return configuration_service.get_environment_templates()


@router.get("/scenario-types", response_model=list[GetScenarioType], response_model_exclude_none=True)
async def get_scenario_type_list() -> list[GetScenarioType]:
    return configuration_service.get_scenario_types()
