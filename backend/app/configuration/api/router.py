from fastapi import APIRouter

from backend.app.configuration.api.v2 import router as configuration_v2_router

v2 = APIRouter(prefix="/api/v2")
v2.include_router(configuration_v2_router)
