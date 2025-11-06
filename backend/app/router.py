from fastapi import APIRouter

from backend.app.agent.api.router import v1 as agent_v1

route = APIRouter()
route.include_router(agent_v1)
