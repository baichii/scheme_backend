from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.deduction_run.model.deduction_run import (
    DeductionRun,
    DeductionRuntimeMessage,
    DeductionTask,
)

ACTIVE_RUN_STATUSES = ("starting", "running", "stopping")


class CRUDDeductionRun(CRUDPlus[DeductionRun]):
    async def get(self, db: AsyncSession, pk: int, *, for_update: bool = False) -> DeductionRun | None:
        statement = select(DeductionRun).where(DeductionRun.id == pk)
        if for_update:
            statement = statement.with_for_update()
        return (await db.execute(statement)).scalar_one_or_none()

    async def get_active_by_deduction(self, db: AsyncSession, deduction_id: int) -> DeductionRun | None:
        result = await db.execute(
            select(DeductionRun).where(
                DeductionRun.deduction_id == deduction_id,
                DeductionRun.status.in_(ACTIVE_RUN_STATUSES),
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self, db: AsyncSession) -> list[DeductionRun]:
        result = await db.execute(select(DeductionRun).where(DeductionRun.status.in_(ACTIVE_RUN_STATUSES)))
        return list(result.scalars())

    async def get_latest_by_deduction_ids(
        self, db: AsyncSession, deduction_ids: list[int]
    ) -> dict[int, DeductionRun]:
        if not deduction_ids:
            return {}
        latest = (
            select(DeductionRun.deduction_id, func.max(DeductionRun.id).label("run_id"))
            .where(DeductionRun.deduction_id.in_(deduction_ids))
            .group_by(DeductionRun.deduction_id)
            .subquery()
        )
        rows = await db.execute(select(DeductionRun).join(latest, DeductionRun.id == latest.c.run_id))
        return {run.deduction_id: run for run in rows.scalars()}

    async def create(self, db: AsyncSession, values: dict) -> DeductionRun:
        run = DeductionRun(**values)
        db.add(run)
        await db.flush()
        return run

    async def update(self, db: AsyncSession, pk: int, values: dict) -> None:
        await db.execute(update(DeductionRun).where(DeductionRun.id == pk).values(**values))
        await db.flush()


class CRUDDeductionTask(CRUDPlus[DeductionTask]):
    async def get(self, db: AsyncSession, pk: int) -> DeductionTask | None:
        return await self.select_model(db, pk)

    async def get_by_run(self, db: AsyncSession, run_id: int) -> list[DeductionTask]:
        result = await db.execute(
            select(DeductionTask).where(DeductionTask.run_id == run_id).order_by(DeductionTask.id.asc())
        )
        return list(result.scalars())

    async def create_many(self, db: AsyncSession, values: list[dict]) -> list[DeductionTask]:
        tasks = [DeductionTask(**item) for item in values]
        db.add_all(tasks)
        await db.flush()
        return tasks

    async def update(self, db: AsyncSession, pk: int, values: dict) -> None:
        await db.execute(update(DeductionTask).where(DeductionTask.id == pk).values(**values))
        await db.flush()


class CRUDDeductionRuntimeMessage(CRUDPlus[DeductionRuntimeMessage]):
    async def create(self, db: AsyncSession, values: dict) -> DeductionRuntimeMessage:
        message = DeductionRuntimeMessage(**values)
        db.add(message)
        await db.flush()
        return message

    async def get_after(
        self,
        db: AsyncSession,
        *,
        run_id: int,
        sequence: int,
        limit: int = 500,
    ) -> list[DeductionRuntimeMessage]:
        result = await db.execute(
            select(DeductionRuntimeMessage)
            .where(
                DeductionRuntimeMessage.run_id == run_id,
                DeductionRuntimeMessage.sequence > sequence,
            )
            .order_by(DeductionRuntimeMessage.sequence.asc())
            .limit(limit)
        )
        return list(result.scalars())

    async def get_history(
        self,
        db: AsyncSession,
        *,
        run_id: int,
        message_type: str,
        before_sequence: int | None,
        limit: int,
        task_id: int | None = None,
        branch_node_id: str | None = None,
    ) -> list[DeductionRuntimeMessage]:
        filters = [
            DeductionRuntimeMessage.run_id == run_id,
            DeductionRuntimeMessage.type == message_type,
        ]
        if before_sequence is not None:
            filters.append(DeductionRuntimeMessage.sequence < before_sequence)
        if task_id is not None:
            filters.append(DeductionRuntimeMessage.task_id == task_id)
        if branch_node_id is not None:
            filters.append(DeductionRuntimeMessage.branch_node_id == branch_node_id)
        result = await db.execute(
            select(DeductionRuntimeMessage)
            .where(*filters)
            .order_by(DeductionRuntimeMessage.sequence.desc())
            .limit(limit + 1)
        )
        return list(result.scalars())


deduction_run_dao: CRUDDeductionRun = CRUDDeductionRun(DeductionRun)
deduction_task_dao: CRUDDeductionTask = CRUDDeductionTask(DeductionTask)
deduction_runtime_message_dao: CRUDDeductionRuntimeMessage = CRUDDeductionRuntimeMessage(
    DeductionRuntimeMessage
)
