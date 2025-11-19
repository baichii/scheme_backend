from fastapi import APIRouter

from backend.app.deduction.schema.task_log import GetTaskLogDetail
from backend.app.deduction.service.task_log_service import task_log_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession


# Note: task log service only provides read-only APIs
# Todo: 需要提供更多自定义的查询接口，通过任务id，通过推演id，需要定接口和分页逻辑
router = APIRouter()


@router.get("/by-task-id/{task_id}", summary="根据任务ID获取任务日志")
async def get_task_logs_by_task_id(db: CurrentSession, task_id: int) -> ResponseSchemaModel[list[GetTaskLogDetail]]:
    """根据任务ID获取任务日志"""
    task_logs = await task_log_service.get_by_task_id(db=db, task_id=task_id)
    return response_base.success(data=task_logs)

