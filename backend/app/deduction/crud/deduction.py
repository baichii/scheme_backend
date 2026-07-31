from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.deduction.model.deduction import Deduction
from backend.app.deduction.schema.deduction import CreateDeductionInternal
from backend.app.deduction_run.model.deduction_run import DeductionRun


class CRUDDeduction(CRUDPlus[Deduction]):
    """推演方案数据库操作类。"""

    async def get(self, db: AsyncSession, pk: int) -> Deduction | None:
        """获取推演方案。"""

        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> Deduction | None:
        """通过名称获取推演方案。"""

        return await self.select_model_by_column(db, normalized_name=name.casefold())

    async def get_all(self, db: AsyncSession) -> list[Deduction]:
        """获取全部推演方案，用于跨域引用检查。"""

        result = await db.execute(select(Deduction))
        return list(result.scalars())

    async def get_list(
        self,
        db: AsyncSession,
        *,
        status: str,
        search: str,
        page: int,
        page_size: int,
        sort_order: str,
        run_status: str = "all",
    ) -> tuple[list[Deduction], int]:
        """获取推演方案分页列表。"""

        filters = []
        if status != "all":
            filters.append(Deduction.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(func.lower(Deduction.name + " " + Deduction.description).like(pattern))

        latest_run = (
            select(DeductionRun.deduction_id, func.max(DeductionRun.id).label("run_id"))
            .group_by(DeductionRun.deduction_id)
            .subquery()
        )
        statement = select(Deduction)
        count_statement = select(func.count()).select_from(Deduction)
        if run_status != "all":
            statement = statement.join(latest_run, latest_run.c.deduction_id == Deduction.id).join(
                DeductionRun, DeductionRun.id == latest_run.c.run_id
            )
            count_statement = count_statement.join(
                latest_run, latest_run.c.deduction_id == Deduction.id
            ).join(DeductionRun, DeductionRun.id == latest_run.c.run_id)
            filters.append(DeductionRun.status == run_status)

        total = int((await db.scalar(count_statement.where(*filters))) or 0)
        updated_at = func.coalesce(Deduction.update_at, Deduction.create_at)
        ordering = updated_at.asc() if sort_order == "asc" else updated_at.desc()
        result = await db.execute(
            statement.where(*filters)
            .order_by(ordering, Deduction.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total

    async def create(self, db: AsyncSession, obj: CreateDeductionInternal) -> Deduction:
        """创建推演方案。"""

        deduction = await self.create_model(db, obj, flush=True)
        await db.refresh(deduction)
        return deduction

    async def update(self, db: AsyncSession, pk: int, values: dict) -> int:
        """更新推演方案。"""

        return await self.update_model(db, pk, values, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """删除推演方案。"""

        return await self.delete_model(db, pk, flush=True)


deduction_dao: CRUDDeduction = CRUDDeduction(Deduction)
