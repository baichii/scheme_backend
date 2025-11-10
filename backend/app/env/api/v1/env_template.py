from fastapi import APIRouter

from backend.app.env.schema.env_template import CreateEnvTemplateParam, GetEnvTemplateDetail
from backend.app.env.service.env_template_service import env_template_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get("/all", summary="获取所有环境配置模版")
async def get_all_env_templates(db: CurrentSession) -> ResponseSchemaModel[list[GetEnvTemplateDetail]]:
    """获取所有环境配置模版"""
    env_templates = await env_template_service.get_all(db=db)
    return response_base.success(data=env_templates)


@router.get("/{pk}", summary="根据ID获取环境配置模版")
async def get_env_template_by_id(db: CurrentSession, pk: int) -> ResponseSchemaModel[GetEnvTemplateDetail]:
    """根据ID获取环境配置模版"""
    env_template = await env_template_service.get(db=db, pk=pk)
    return response_base.success(data=env_template)


@router.get("/{name}", summary="根据名称获取环境配置模版")
async def get_env_template_by_name(db: CurrentSession, name: str) -> ResponseSchemaModel[GetEnvTemplateDetail]:
    """根据名称获取环境配置模版"""
    env_template = await env_template_service.get_by_name(db=db, name=name)
    return response_base.success(data=env_template)


@router.post("/create", summary="创建环境配置模版")
async def create_env_template(
    db: CurrentSessionTransaction, obj: CreateEnvTemplateParam
) -> ResponseModel:
    """创建环境配置模版"""
    await env_template_service.create(db=db, obj=obj)
    return response_base.success()


@router.delete("/{pk}", summary="根据ID删除环境配置模版")
async def delete_env_template(db: CurrentSessionTransaction, pk: int) -> ResponseModel:
    """根据ID删除环境配置模版"""
    count = await env_template_service.delete(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete("/all", summary="删除所有环境配置模版")
async def delete_all_env_templates(db: CurrentSessionTransaction) -> ResponseModel:
    """删除所有环境配置模版"""
    count = await env_template_service.delete_all(db=db)
    if count >= 0:
        return response_base.success()
    return response_base.fail()