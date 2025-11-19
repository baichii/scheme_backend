from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent.model.agent_meta import AgentMeta
from backend.app.agent.schema.agent_meta import CreateAgentInternal


class CRUDAgentMeta(CRUDPlus[AgentMeta]):
    """智能体元数据数据库操作类"""

    async def get(self, db: AsyncSession, agent_id: int) -> AgentMeta | None:
        """根据智能体ID获取智能体元数据"""
        return await self.select_model(db, agent_id)

    async def get_all(self, db: AsyncSession) -> Sequence[AgentMeta]:
        """获取所有智能体元数据"""
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj: CreateAgentInternal) -> AgentMeta:
        """创建智能体元数据"""
        return await self.create_model(db, obj, flush=True)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """根据智能体ID删除智能体元数据"""
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


agent_meta_dao: CRUDAgentMeta = CRUDAgentMeta(AgentMeta)
