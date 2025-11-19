from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.scheme.crud.scheme import scheme_dao
from backend.app.scheme.model.scheme import Scheme
from backend.app.scheme.schema.scheme import CreateSchemeInternal, CreateSchemeParam, UpdateSchemeParam
from backend.common.exception import errors
from backend.utils.snowflake import snowflake


class SchemeService:
    """配置服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Scheme | None:
        """获取方案配置"""
        scheme = await scheme_dao.get(db, pk)
        if not scheme:
            raise errors.NotFoundError(msg="方案配置不存在")
        return scheme

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[Scheme]:
        """获取所有方案配置"""
        schemes = await scheme_dao.get_all(db)
        return schemes

    @staticmethod
    async def get_by_name(*, db: AsyncSession, name: str) -> Scheme | None:
        """根据名称获取方案配置"""
        scheme = await scheme_dao.get_by_name(db, name)
        if not scheme:
            raise errors.NotFoundError(msg="方案配置不存在")
        return scheme

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateSchemeParam) -> None:
        """创建方案配置"""

        unique_id = snowflake.generate_id()
        obj = CreateSchemeInternal(id=unique_id, **obj.model_dump())
        await scheme_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateSchemeParam) -> int:
        """更新方案配置"""
        scheme = await scheme_dao.get(db, pk)
        if not scheme:
            raise errors.NotFoundError(msg="方案配置不存在")
        await scheme_dao.update(db, pk, obj)
        return 1

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除方案配置"""
        scheme = await scheme_dao.delete(db, pk)
        if not scheme:
            raise errors.NotFoundError(msg="方案配置不存在")
        return 1


scheme_service: SchemeService = SchemeService()
