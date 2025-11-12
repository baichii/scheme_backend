from fastapi import APIRouter

from backend.app.scheme.schema.scheme import CreateSchemeParam, GetSchemeDetail
from backend.app.scheme.service.scheme_service import scheme_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get("/all", summary="获取所有方案配置")
async def get_all_schemes(db: CurrentSession) -> ResponseSchemaModel[list[GetSchemeDetail]]:
    """获取所有方案配置"""
    schemes = await scheme_service.get_all(db=db)

    return response_base.success(data=schemes)


@router.get("/{pk}", summary="获取方案配置详情")
async def get_scheme_by_id(db: CurrentSession, pk: int) -> ResponseSchemaModel[GetSchemeDetail]:
    """获取方案配置详情"""
    scheme = await scheme_service.get(db=db, pk=pk)
    return response_base.success(data=scheme)


@router.get("/by-name/{name}", summary="根据名称获取方案配置详情")
async def get_scheme_by_name(db: CurrentSession, name: str) -> ResponseSchemaModel[GetSchemeDetail]:
    """根据名称获取方案配置详情"""
    scheme = await scheme_service.get_by_name(db=db, name=name)
    return response_base.success(data=scheme)


@router.post("/create", summary="创建方案配置")
async def create_scheme(db: CurrentSessionTransaction, param: CreateSchemeParam) -> ResponseModel:
    """创建方案配置"""
    await scheme_service.create(db=db, obj=param)
    return response_base.success()


@router.delete("/{pk}", summary="根据ID删除方案配置")
async def delete_scheme(db: CurrentSessionTransaction, pk: int) -> ResponseModel:
    """删除方案配置"""
    await scheme_service.delete(db=db, pk=pk)
    return response_base.success()
