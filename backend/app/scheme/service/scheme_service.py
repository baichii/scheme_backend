from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.scheme.crud.scheme import scheme_dao
from backend.app.scheme.model.scheme import Scheme
from backend.app.scheme.schema.scheme import CreateSchemeParam, CreateSchemeInternal
from backend.common.exception import errors


class SchemeService:
    """方案配置服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Scheme | None:
        """获取方案配置"""
        scheme = await scheme_dao.get(db, pk)
        if not scheme:
            raise errors.NotFoundError(msg=f"方案配置不存在")
        return scheme

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[Scheme]:
        """获取所有方案配置"""
        return await scheme_dao.get_all(db)

    @staticmethod
    async def get_by_name(*, db: AsyncSession, name: str) -> Scheme | None:
        """根据名称获取方案配置"""
        scheme = await scheme_dao.get_by_name(db, name)
        if not scheme:
            raise errors.NotFoundError(msg=f"方案配置不存在")
        return scheme

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateSchemeParam) -> None:
        """创建方案配置"""

        # fixme: 这里预留前端配置和写入数据库配置的转换逻辑, 感觉数据会有差异, 但工程还没有遇到
        obj = CreateSchemeInternal(**obj.model_dump())
        await scheme_dao.create(db, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除方案配置"""
        scheme = await scheme_dao.delete(db, pk)
        if not scheme:
            raise errors.NotFoundError(msg=f"方案配置不存在")
        return 1


scheme_service: SchemeService = SchemeService()
