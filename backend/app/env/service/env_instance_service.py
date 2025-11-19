from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.env.crud.crud_env_instance import env_instance_dao
from backend.app.env.crud.crud_env_template import env_template_dao
from backend.app.env.model.env_instance import EnvInstance
from backend.app.env.schema.env_instance import CreateEnvInstanceParam
from backend.common.exception import errors


class EnvInstanceService:
    """环境实例服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> EnvInstance | None:
        """获取环境配置实例"""
        env_instance = await env_instance_dao.get(db, pk)
        if not env_instance:
            raise errors.NotFoundError(msg="环境配置实例不存在")
        return env_instance

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[EnvInstance]:
        """获取所有环境配置实例"""
        env_instances = await env_instance_dao.get_all(db)
        return env_instances

    @staticmethod
    async def get_by_name(*, db: AsyncSession, name: str) -> EnvInstance | None:
        """根据名称获取环境配置实例"""
        env_instance = await env_instance_dao.get_by_name(db, name)
        if not env_instance:
            raise errors.NotFoundError(msg="环境配置实例不存在")
        return env_instance

    @staticmethod
    async def get_by_template_id(*, db: AsyncSession, template_id: int) -> Sequence[EnvInstance]:
        """根据模版 ID 获取环境配置实例"""
        env_instances = await env_instance_dao.get_by_template_id(db, template_id)
        return env_instances

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateEnvInstanceParam) -> EnvInstance:
        """创建环境配置实例"""
        # 验证模板是否存在
        template = await env_template_dao.get(db, obj.template_id)
        if not template:
            raise errors.NotFoundError(msg="环境配置模版不存在")
        # 检查名称是否重复
        env_instance = await env_instance_dao.get_by_name(db, obj.name)
        if env_instance:
            raise errors.ConflictError(msg="环境配置实例名称已存在")
        return await env_instance_dao.create(db, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除环境配置实例"""
        env_instance = await env_instance_dao.get(db, pk)
        if not env_instance:
            raise errors.NotFoundError(msg="环境配置实例不存在")
        count = await env_instance_dao.delete(db, pk)
        return count

    @staticmethod
    async def delete_all(*, db: AsyncSession) -> int:
        """删除所有环境配置实例"""
        from sqlalchemy import delete
        from backend.app.env.model.env_instance import EnvInstance

        stmt = delete(EnvInstance)
        result = await db.execute(stmt)
        return result.rowcount


env_instance_service: EnvInstanceService = EnvInstanceService()
