from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.env.crud.crud_env_template import env_template_dao
from backend.app.env.model.env_template import EnvTemplate
from backend.app.env.schema.env_template import CreateEnvTemplateParam
from backend.common.exception import errors


class EnvTemplateService:
    """环境配置模版服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> EnvTemplate | None:
        """获取环境配置模版"""
        env_template = await env_template_dao.get(db, pk)
        if not env_template:
            raise errors.NotFoundError(msg="环境配置模版不存在")
        return env_template

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[EnvTemplate]:
        """获取所有环境配置模版"""
        env_templates = await env_template_dao.get_all(db)
        return env_templates

    @staticmethod
    async def get_by_name(*, db: AsyncSession, name: str) -> EnvTemplate | None:
        """根据名称获取环境配置模版"""
        env_template = await env_template_dao.get_by_name(db, name)
        if not env_template:
            raise errors.NotFoundError(msg="环境配置模版不存在")
        return env_template

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateEnvTemplateParam) -> EnvTemplate:
        """创建环境配置模版"""
        env_template = await env_template_dao.get_by_name(db, obj.name)
        if env_template:
            raise errors.ConflictError(msg="环境配置模版名称已存在")
        return await env_template_dao.create(db, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除环境配置模版"""
        env_template = await env_template_dao.get(db, pk)
        if not env_template:
            raise errors.NotFoundError(msg="环境配置模版不存在")
        count = await env_template_dao.delete(db, pk)
        return count

    @staticmethod
    async def delete_all(*, db: AsyncSession) -> int:
        """删除所有环境配置模版"""
        from sqlalchemy import delete
        from backend.app.env.model.env_template import EnvTemplate

        stmt = delete(EnvTemplate)
        result = await db.execute(stmt)
        return result.rowcount


env_template_service: EnvTemplateService = EnvTemplateService()
