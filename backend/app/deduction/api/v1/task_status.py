from fastapi import APIRouter

from backend.app.deduction.schema.task_status import GetTaskStatusDetail
from backend.app.deduction.service.task_status_service import task_status_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get("/{pk}", summary="获取任务状态详情")
async def get_task_status_by_id(db: CurrentSession, pk: int) -> ResponseSchemaModel[GetTaskStatusDetail]:
    """获取任务状态详情"""
    task_status = await task_status_service.get(db=db, pk=pk)
    return response_base.success(data=task_status)


@router.get("/by-deduce-id")
async def get_task_status_by_deduce_id(db: CurrentSession, deduce_id: int) -> ResponseSchemaModel[GetTaskStatusDetail]:
    """根据推演ID获取任务状态详情"""
    task_status = await task_status_service.get_by_deduce_id(db=db, deduce_id=deduce_id)
    return response_base.success(data=task_status)
