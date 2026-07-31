from fastapi import APIRouter

from backend.app.deduction.api.v2.deduction import router as deduction_v2_router

v2 = APIRouter(prefix="/api/v2")
v2.include_router(deduction_v2_router)
