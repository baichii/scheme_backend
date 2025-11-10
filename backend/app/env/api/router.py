from fastapi import APIRouter

from backend.app.env.api.v1.env_instance import router as env_instance_router
from backend.app.env.api.v1.env_template import router as env_template_router
from backend.core.conf import settings

v1 = APIRouter(prefix=f"{settings.FAST_API_V1_PATH}/env", tags=["环境配置模版"])

v1.include_router(env_template_router, prefix="/template")
v1.include_router(env_instance_router, prefix="/instance")
