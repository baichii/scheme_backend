from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.deduction.model.task_status import TaskStatus
from backend.app.deduction.schema.task_status import CreateTaskStatusParam, UpdateTaskStatusParam


class CRUDTaskStatus(CRUDPlus[TaskStatus]):
    """任务状态数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> TaskStatus | None:
        """获取任务状态"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[TaskStatus]:
        """获取所有任务状态"""
        return await self.select_models(db)

    async def get_by_deduce_id(self, db: AsyncSession, deduce_id: int) -> Sequence[TaskStatus]:
        """根据推演id获取任务状态"""
        return await self.select_models(db, deduce_id__eq=deduce_id)

    async def create(self, db: AsyncSession, obj: CreateTaskStatusParam) -> TaskStatus:
        """创建任务状态"""
        return await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateTaskStatusParam) -> int:
        """更新任务状态"""
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """批量删除任务状态"""
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


task_status_dao: CRUDTaskStatus = CRUDTaskStatus(TaskStatus)
