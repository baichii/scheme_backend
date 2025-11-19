from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deduction.crud.task_status import task_status_dao
from backend.app.deduction.model.task_status import TaskStatus
from backend.app.deduction.schema.task_status import CreateTaskStatusParam, CreateTaskStatusInternal, UpdateTaskStatusParam
from backend.common.exception import errors
from backend.utils.snowflake import snowflake


class TaskStatusService:
    """任务状态服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> TaskStatus | None:
        """获取任务状态"""
        task_status = await task_status_dao.get(db, pk)
        if not task_status:
            raise errors.NotFoundError(msg="任务状态不存在")
        return task_status
    @staticmethod
    async def get_by_deduce_id(*, db: AsyncSession, deduce_id: int) -> Sequence[TaskStatus]:
        """根据推演ID获取任务状态"""
        task_statuses = await task_status_dao.get_by_deduce_id(db, deduce_id)
        return task_statuses

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[TaskStatus]:
        """获取所有任务状态"""
        task_statuses = await task_status_dao.get_all(db)
        return task_statuses

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateTaskStatusParam) -> TaskStatus:
        """创建任务状态"""
        unique_id = snowflake.generate()
        obj = CreateTaskStatusInternal(id=unique_id, **obj.model_dump())
        return await task_status_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateTaskStatusParam) -> int:
        """更新任务状态"""
        return await task_status_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        """删除任务状态"""
        return await task_status_dao.delete(db, pks)


task_status_service: TaskStatusService = TaskStatusService()

