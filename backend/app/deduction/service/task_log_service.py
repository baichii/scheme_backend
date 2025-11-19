from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deduction.crud.task_log import task_log_dao
from backend.app.deduction.model.task_log import TaskLog
from backend.app.deduction.schema.task_log import CreateTaskLogParam
from backend.common.exception import errors


class TaskLogService:
    """任务日志服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> TaskLog | None:
        """获取任务日志"""
        task_log = await task_log_dao.get(db, pk)
        if not task_log:
            raise errors.NotFoundError(msg="任务日志不存在")
        return task_log

    @staticmethod
    async def get_by_task_id(*, db: AsyncSession, task_id: int) -> Sequence[TaskLog]:
        """根据任务ID获取任务日志"""
        task_logs = await task_log_dao.get_by_task_id(db, task_id)
        return task_logs

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateTaskLogParam) -> None:
        """创建任务日志"""
        await task_log_dao.create(db, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除任务日志"""
        task_log = await task_log_dao.delete(db, pk)
        if not task_log:
            raise errors.NotFoundError(msg="任务日志不存在")
        return 1

task_log_service: TaskLogService = TaskLogService()
