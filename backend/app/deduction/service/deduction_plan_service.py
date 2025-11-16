from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deduction.crud.deduction_plan import deduction_plan_dao
from backend.app.deduction.model.deduction_plan import DeductionPlan
from backend.app.deduction.schema.deduction_plan import CreateDeductionPlanParam, CreateDeductionPlanInternal
from backend.common.exception import errors
from backend.utils.snowflake import snowflake
from backend.common.enums import DeductionPlanStatus


class DeductionPlanService:
    """推理方案服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> DeductionPlan | None:
        """获取推理方案"""
        deduction_plan = await deduction_plan_dao.get(db, pk)
        if not deduction_plan:
            raise errors.NotFoundError(msg="推理方案不存在")
        return deduction_plan

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[DeductionPlan]:
        """获取所有推理方案"""
        deduction_plans = await deduction_plan_dao.get_all(db)
        return deduction_plans

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDeductionPlanParam):
        """创建推理方案"""

        unique_id = snowflake.generate()
        obj_internal = CreateDeductionPlanInternal(
            id=unique_id,
            **obj.model_dump(),
            status=DeductionPlanStatus.INACTIVE,
        )
        await deduction_plan_dao.create(db, obj_internal)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除推理方案"""
        deduction_plan = await deduction_plan_dao.delete(db, pk)
        if not deduction_plan:
            raise errors.NotFoundError(msg="推理方案不存在")
        return 1

deduction_plan_service: DeductionPlanService = DeductionPlanService()
