from fastapi import APIRouter

from backend.app.branch_scheme.api.v2 import router as branch_scheme_v2_router

v2 = APIRouter(prefix="/api/v2")
v2.include_router(branch_scheme_v2_router)
