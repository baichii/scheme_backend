from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.env.model.env import EnvInstance, EnvTemplate
from backend.app.env.scheme.env import EnvInstanceRequest, EnvTemplateRequest
from backend.common.exception.errors import HTTPException
from backend.utils.snowflake import snowflake


class EnvService:
    """环境配置服务"""

    @staticmethod
    async def create_env_template(db: AsyncSession, env_template: EnvTemplateRequest):
        """创建环境配置模版"""
        env_template_id = snowflake.generate_id()
        db_env_template = EnvTemplate(
            env_template_id=env_template_id,
            env_template_name=env_template.env_template_name,
            param_schema=env_template.param_schema,
        )
        db.add(db_env_template)
        await db.commit()
        return db_env_template

    @staticmethod
    async def create_env_instance(db: AsyncSession, env_instance: EnvInstanceRequest):
        """创建环境配置实例"""
        env_instance_id = snowflake.generate_id()
        db_env_instance = EnvInstance(
            env_instance_id=env_instance_id,
            env_template_id=env_instance.env_template_id,
            params=env_instance.params,
        )
        db.add(db_env_instance)
        await db.commit()
        return db_env_instance

    @staticmethod
    async def get_env_instance(db: AsyncSession, env_instance_id: int):
        """获取环境配置实例"""
        db_env_instance = await db.get(EnvInstance, env_instance_id)
        if db_env_instance is None:
            raise HTTPException(status_code=404, detail="环境配置实例不存在")
        return db_env_instance
