from datetime import datetime

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent.model.agent_meta import AgentMeta


class CRUDAgent(CRUDPlus):
    """智能体数据库操作类"""

    @staticmethod
    async def get(db: AsyncSession, agent_id: int) -> AgentMeta | None:
        """根据智能体ID获取智能体"""
        return await db.get()


