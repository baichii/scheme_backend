from fastapi import APIRouter

from backend.app.agent.api.v1.agent_meta import router as agent_meta_router
from backend.core.conf import settings

v1 = APIRouter(prefix=f"{settings.FAST_API_V1_PATH}/agent_meta", tags=["智能体元数据"])

v1.include_router(agent_meta_router)
