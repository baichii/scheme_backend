from fastapi import APIRouter

from backend.app.agent.api.v1.agent_meta import router as upload_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FAST_API_V1_PATH)

v1.include_router(upload_router)
