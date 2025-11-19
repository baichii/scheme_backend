from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.deduction.model.task_log import TaskLog
from backend.app.deduction.schema.task_log import CreateTaskLogParam


class CRUDTaskLog(CRUDPlus[TaskLog]):
    """任务日志数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> TaskLog | None:
        """获取任务日志"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[TaskLog]:
        """获取所有任务日志"""
        return await self.select_models(db)

    async def get_by_task_id(self, db: AsyncSession, task_id: int) -> Sequence[TaskLog]:
        """根据任务ID获取任务日志"""
        return await self.select_models(db, task_id__eq=task_id)

    async def create(self, db: AsyncSession, obj: CreateTaskLogParam) -> int:
        """创建任务日志"""
        ins = await self.create_model(db, obj, flush=True)
        return ins.id

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """批量删除任务日志"""
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


task_log_dao: CRUDTaskLog = CRUDTaskLog(TaskLog)
