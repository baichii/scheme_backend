from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.env.crud.crud_env_template import env_template_dao
from backend.app.env.model.env_template import EnvTemplate
from backend.app.env.schema.env_template import EnvTemplateParam
from backend.common.exception import errors


class EnvTemplateService:
    """环境配置模版服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> EnvTemplate:
        """获取环境配置模版"""
        return await env_template_dao.get(db, pk)

    @staticmethod
    async def get_by_name(*, db: AsyncSession, name: str) -> EnvTemplate:
        """根据名称获取环境配置模版"""
        if await env_template_dao.get_by_name(db, name):
            return await env_template_dao.get_by_name(db, name)
        raise errors.NotFoundError(msg="环境配置模版不存在")

    @staticmethod
    async def get_all(*, db: AsyncSession) -> list[EnvTemplate]:
        """获取所有环境配置模版"""
        return await env_template_dao.get_all(db)

    @staticmethod
    async def create(*, db: AsyncSession, obj: EnvTemplateParam) -> None:
        """创建环境配置模版"""
        if await env_template_dao.get_by_name(db, obj.name):
            raise errors.ConflictError(msg="环境配置模版名称已存在")
        await env_template_dao.create(db, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> bool:
        """删除环境配置模版"""
        if not await env_template_dao.get(db, pk):
            raise errors.NotFoundError(msg="环境配置模版不存在")
        return await env_template_dao.delete(db, pk)


env_template_service: EnvTemplateService = EnvTemplateService()
