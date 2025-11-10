from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.env.model.env_template import EnvTemplate
from backend.app.env.schema.env_template import CreateEnvTemplateParam


class CRUDEnvTemplate(CRUDPlus[EnvTemplate]):
    """环境配置模版数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> EnvTemplate | None:
        """获取环境配置模版"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[EnvTemplate]:
        """获取所有环境配置模版"""
        return await self.select_models(db)

    async def get_by_name(self, db: AsyncSession, name: str) -> EnvTemplate | None:
        """根据名称获取环境配置模版"""
        return await self.select_model_by_column(db, name=name)

    async def create(self, db: AsyncSession, obj: CreateEnvTemplateParam) -> None:
        """创建环境配置模版"""
        await self.create_model(db, obj, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """删除环境配置模版"""
        env_template = await self.get(db, pk)
        await db.delete(env_template)
        return 1


env_template_dao: CRUDEnvTemplate = CRUDEnvTemplate(EnvTemplate)
