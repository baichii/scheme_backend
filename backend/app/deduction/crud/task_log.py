from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.deduction.model.task_log import TaskLog
from backend.app.deduction.schema.task_log import CreateTaskLogParam, GetTaskLogDetail
from backend.common.exception import errors


class CRUDTaskLog(CRUDPlus[TaskLog]):
    """任务日志数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> TaskLog | None:
        """获取任务日志"""
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[TaskLog]:
        """获取所有任务日志"""
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj: CreateTaskLogParam) -> None:
        """创建任务日志"""
        await self.create_model(db, obj, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        """删除任务日志"""
        task_log = await self.get(db, pk)
        if not task_log:
            return 0
        await db.delete(task_log)
        return 1

task_log_dao: CRUDTaskLog = CRUDTaskLog(TaskLog)
