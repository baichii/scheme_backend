from fastapi import APIRouter

from backend.app.deduction.api.v1.deduction_plan import router as deduction_plan_router
from backend.app.deduction.api.v1.task_log import router as task_log_router
from backend.app.deduction.api.v1.task_status import router as task_status_router
from backend.core.conf import settings

v1 = APIRouter(prefix=f"{settings.FAST_API_V1_PATH}/deduction", tags=["推演管理"])

v1.include_router(deduction_plan_router)
v1.include_router(task_log_router)
v1.include_router(task_status_router)
