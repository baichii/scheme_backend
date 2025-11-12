from fastapi import APIRouter

from backend.app.scheme.api.v1.scheme import router as scheme_router
from backend.core.conf import settings

v1 = APIRouter(prefix=f"{settings.FAST_API_V1_PATH}/scheme", tags=["方案配置"])

v1.include_router(scheme_router)
