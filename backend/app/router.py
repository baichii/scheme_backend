from fastapi import APIRouter

from backend.app.branch_scheme.api.router import v2 as branch_scheme_v2
from backend.app.configuration.api.router import v2 as configuration_v2
from backend.app.deduction.api.router import v2 as deduction_v2
from backend.app.deduction_run.api.router import v2 as deduction_run_v2
from backend.app.resource.api.router import v2 as resource_v2

route = APIRouter()

route.include_router(branch_scheme_v2)
route.include_router(configuration_v2)
route.include_router(deduction_v2)
route.include_router(deduction_run_v2)
route.include_router(resource_v2)
