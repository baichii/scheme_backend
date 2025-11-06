
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent.model.agent import Agent
from backend.app.agent.schema.agent_meta import AgentCreateRequest


class CRUDAgent(CRUDPlus[Agent]):
    """智能体数据库操作类"""

    async def get(self, db: AsyncSession, agent_id: int) -> Agent | None:
        """根据智能体ID获取智能体"""
        return await db.get(Agent, agent_id)

    async def create(self, db: AsyncSession, obj_in: AgentCreateRequest) -> Agent:
        """创建智能体"""
        agent = Agent(
            agent_name=obj_in.agent_name,
            agent_load=obj_in.agent_load,
            agent_desc=obj_in.agent_desc,
            agent_url=obj_in.agent_url,
            side=obj_in.side,
            param_schema=obj_in.param_schema,
            supported_env_templates=obj_in.supported_env_templates,
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent

    async def delete(self, db: AsyncSession, agent_id: int) -> bool:
        """删除智能体"""
        agent = await self.get(db, agent_id)
        if not agent:
            return False
        await db.delete(agent)
        await db.commit()
        return True

    async def list_all(self, db: AsyncSession) -> list[Agent]:
        """获取所有智能体"""
        stmt = select(Agent)
        result = await db.execute(stmt)
        return list(result.scalars().all())


# 单例模式
crud_agent = CRUDAgent(Agent)



