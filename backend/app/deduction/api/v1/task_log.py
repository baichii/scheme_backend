from fastapi import APIRouter

from backend.app.deduction.schema.task_log import GetTaskLogDetail
from backend.app.deduction.service import task_log_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession, CurrentSessionTransaction


# Note: task log service only provides read-only APIs
# Todo: 需要提供更多自定义的查询接口，通过任务id，通过推演id，需要定接口和分页逻辑
router = APIRouter()

@router.get("/all", summary="获取所有任务日志")
async def get_all_task_logs(db: CurrentSession) -> ResponseSchemaModel[list[GetTaskLogDetail]]:
    """获取所有任务日志"""
    task_logs = await task_log_service.get_all(db=db)
    return response_base.success(data=task_logs)
