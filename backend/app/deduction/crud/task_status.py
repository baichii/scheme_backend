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

    async def create(self, db: AsyncSession, obj: CreateTaskStatusParam) -> None:
        """创建任务状态"""
        await self.create_model(db, obj, flush=True)

    async def update(self, db: AsyncSession, obj: UpdateTaskStatusParam) -> None:
        """更新任务状态"""
        await self.update_model(db, obj.task_id, obj, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """删除任务状态"""
        task_status = await self.get(db, pk)
        if not task_status:
            return 0
        await db.delete(task_status)
        return 1

task_status_dao: CRUDTaskStatus = CRUDTaskStatus(TaskStatus)
