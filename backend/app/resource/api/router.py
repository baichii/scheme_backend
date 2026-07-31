from fastapi import APIRouter

from backend.app.resource.api.v2 import router as resource_v2_router

v2 = APIRouter(prefix="/api/v2")
v2.include_router(resource_v2_router)
