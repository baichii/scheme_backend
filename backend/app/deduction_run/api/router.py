from fastapi import APIRouter

from backend.app.deduction_run.api.v2 import router as deduction_run_v2_router

v2 = APIRouter(prefix="/api/v2")
v2.include_router(deduction_run_v2_router)
