from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.env.model.env_instance import EnvInstance
from backend.app.env.schema.env_instance import CreateEnvInstanceParam, UpdateEnvInstanceParam


class CRUDEnvInstance(CRUDPlus[EnvInstance]):
    """环境配置实例数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> EnvInstance | None:
        """获取环境配置实例"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[EnvInstance]:
        """获取所有环境配置实例"""
        return await self.select_models(db)

    async def get_by_name(self, db: AsyncSession, name: str) -> EnvInstance | None:
        """根据名称获取环境配置实例"""
        return await self.select_model_by_column(db, name=name)

    async def get_by_template_id(self, db: AsyncSession, template_id: int) -> Sequence[EnvInstance]:
        """根据模版 ID 获取环境配置实例"""
        stmt = select(EnvInstance).where(EnvInstance.template_id == template_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj: CreateEnvInstanceParam) -> None:
        """创建环境配置实例"""
        await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, obj: UpdateEnvInstanceParam) -> None:
        """更新环境配置实例"""
        await self.update_model(db, obj, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """删除环境配置实例"""
        env_instance = await self.get(db, pk)
        if not env_instance:
            return 0
        await db.delete(env_instance)
        return 1

env_instance_dao: CRUDEnvInstance = CRUDEnvInstance(EnvInstance)
