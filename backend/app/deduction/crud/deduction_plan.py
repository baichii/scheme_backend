from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.deduction.model.deduction_plan import DeductionPlan
from backend.app.deduction.schema.deduction_plan import CreateDeductionPlanInternal, UpdateDeductionPlanParam


class CRUDDeductionPlan(CRUDPlus[DeductionPlan]):
    """推演方案配置数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> DeductionPlan | None:
        """获取推演方案详情"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[DeductionPlan]:
        """获取所有推演方案配置"""
        return await self.select_models(db)

    async def get_by_name(self, db: AsyncSession, name: str) -> DeductionPlan | None:
        """根据名称获取推演方案配置"""
        return await self.select_model_by_column(db, name=name)

    async def create(self, db: AsyncSession, obj: CreateDeductionPlanInternal) -> DeductionPlan:
        """创建推演方案配置"""
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, obj: UpdateDeductionPlanParam) -> int:
        """更新推演方案"""
        return await self.update_model(db, obj.id, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """批量删除推演方案"""
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


deduction_plan_dao: CRUDDeductionPlan = CRUDDeductionPlan(DeductionPlan)
