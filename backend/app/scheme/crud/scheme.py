from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.scheme.model.scheme import Scheme
from backend.app.scheme.schema.scheme import CreateSchemeInternal


class CRUDScheme(CRUDPlus[Scheme]):
    """方案配置数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Scheme | None:
        """获取方案配置"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[Scheme]:
        """获取所有方案配置"""
        return await self.select_models(db)

    async def get_by_name(self, db: AsyncSession, name: str) -> Scheme | None:
        """根据名称获取方案配置"""
        return await self.select_model_by_column(db, name=name)

    async def create(self, db: AsyncSession, obj: CreateSchemeInternal) -> None:
        """创建方案配置"""
        await self.create_model(db, obj, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """删除方案配置"""
        scheme = await self.get(db, pk)
        if not scheme:
            return 0
        await db.delete(scheme)
        return 1


scheme_dao: CRUDScheme = CRUDScheme(Scheme)
