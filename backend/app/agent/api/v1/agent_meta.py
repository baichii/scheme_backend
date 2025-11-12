

from fastapi import APIRouter, File, UploadFile

from backend.app.agent.schema.agent_meta import CreateAgentParam, GetAgentMetaDetail
from backend.app.agent.service.agent_meta_service import agent_meta_service
from backend.common.response.response_schema import ResponseModel, response_base, ResponseSchemaModel
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get("/all", summary="获取所有智能体元数据")
async def get_all_agent_meta(
    db: CurrentSession
) -> ResponseSchemaModel[list[GetAgentMetaDetail]]:
    """获取所有智能体元数据"""
    agent_meta_list = await agent_meta_service.get_all(db=db)
    return response_base.success(data=agent_meta_list)


@router.get("/{pk}", summary="获取智能体元数据详情")
async def get_agent_meta_by_id(
    db: CurrentSession, pk: int
) -> ResponseSchemaModel[GetAgentMetaDetail]:
    """获取智能体元数据详情"""
    agent_meta = await agent_meta_service.get(db=db, pk=pk)
    return response_base.success(data=agent_meta)


@router.post("/create", summary="创建智能体元数据")
async def create_agent_meta(
    db: CurrentSessionTransaction,
    obj: CreateAgentParam,
    file: UploadFile = File(...)
) -> ResponseModel:
    """创建智能体元数据"""
    await agent_meta_service.create(db=db, obj=obj, file=file)
    return response_base.success()


@router.delete("/{pk}", summary="删除智能体元数据")
async def delete_agent_meta(
    db: CurrentSessionTransaction, pk: int
) -> ResponseModel:
    """删除智能体元数据"""
    count = await agent_meta_service.delete(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
