from fastapi import APIRouter

from backend.app.env.schema.env_instance import (
    CreateEnvInstanceParam,
    GetEnvInstanceDetail,
    UpdateEnvInstanceParam,
)
from backend.app.env.service.env_instance_service import env_instance_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()

@router.get("/all", summary="获取所有环境配置实例")
async def get_all_env_instances(db: CurrentSession) -> ResponseSchemaModel[list[GetEnvInstanceDetail]]:
    """获取所有环境配置实例"""
    env_instances = await env_instance_service.get_all(db=db)
    return response_base.success(data=env_instances)

@router.get("/{pk}", summary="根据ID获取环境配置实例")
async def get_env_instance_by_id(db: CurrentSession, pk: int) -> ResponseSchemaModel[GetEnvInstanceDetail]:
    """根据ID获取环境配置实例"""
    env_instance = await env_instance_service.get(db=db, pk=pk)
    return response_base.success(data=env_instance)


@router.get("/by-name/{name}", summary="根据名称获取环境配置实例")
async def get_env_instance_by_name(db: CurrentSession, name: str) -> ResponseSchemaModel[GetEnvInstanceDetail]:
    """根据名称获取环境配置实例"""
    env_instance = await env_instance_service.get_by_name(db=db, name=name)
    return response_base.success(data=env_instance)


@router.get("/by-template-id/{template_id}", summary="根据模版ID获取环境配置实例")
async def get_env_instance_by_template_id(db: CurrentSession, template_id: int) -> ResponseSchemaModel[list[GetEnvInstanceDetail]]:
    """根据模版ID获取环境配置实例"""
    env_instances = await env_instance_service.get_by_template_id(db=db, template_id=template_id)
    return response_base.success(data=env_instances)


@router.post("/create", summary="创建环境配置实例")
async def create_env_instance(
    db: CurrentSessionTransaction, obj: CreateEnvInstanceParam
) -> ResponseModel:
    """创建环境配置实例"""
    await env_instance_service.create(db=db, obj=obj)
    return response_base.success()

@router.post("/update", summary="更新环境配置实例")
async def update_env_instance(
    db: CurrentSessionTransaction, obj: UpdateEnvInstanceParam
) -> ResponseModel:
    """更新环境配置实例"""
    await env_instance_service.update(db=db, obj=obj)
    return response_base.success()


@router.delete("/{pk}", summary="根据ID删除环境配置实例")
async def delete_env_instance(db: CurrentSessionTransaction, pk: int) -> ResponseModel:
    """根据ID删除环境配置实例"""
    count = await env_instance_service.delete(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete("/all", summary="删除所有环境配置实例")
async def delete_all_env_instances(db: CurrentSessionTransaction) -> ResponseModel:
    """删除所有环境配置实例"""
    count = await env_instance_service.delete_all(db=db)
    if count >= 0:
        return response_base.success()
    return response_base.fail()