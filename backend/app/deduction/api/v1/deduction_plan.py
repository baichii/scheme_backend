from fastapi import APIRouter

from backend.app.deduction.schema.deduction_plan import CreateDeductionPlanParam, GetDeductionPlanParam, UpdateDeductionPlanParam
from backend.app.deduction.service.deduction_plan_service import deduction_plan_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get("/all", summary="获取所有推演方案配置")
async def get_all_deduction_plans(db: CurrentSession) -> ResponseSchemaModel[list[GetDeductionPlanParam]]:
    """获取所有推演方案配置"""
    deduction_plans = await deduction_plan_service.get_all(db=db)
    return response_base.success(data=deduction_plans)


@router.get("/{pk}", summary="获取推演方案配置详情")
async def get_deduction_plan_by_id(db: CurrentSession, pk: int) -> ResponseSchemaModel[GetDeductionPlanParam]:
    """获取推演方案配置详情"""
    deduction_plan = await deduction_plan_service.get(db=db, pk=pk)
    return response_base.success(data=deduction_plan)


@router.post("/create", summary="创建推演方案配置")
async def create_deduction_plan(db: CurrentSessionTransaction, param: CreateDeductionPlanParam) -> ResponseSchemaModel[GetDeductionPlanParam]:
    """创建推演方案配置"""
    deduction_plan = await deduction_plan_service.create(db=db, obj=param)
    return response_base.success(data=deduction_plan.id)


@router.put("/update/{pk}", summary="更新推演方案配置")
async def update_deduction_plan(db: CurrentSessionTransaction, pk: int, param: UpdateDeductionPlanParam) -> ResponseSchemaModel[GetDeductionPlanParam]:
    """更新推演方案配置"""
    deduction_plan = await deduction_plan_service.update(db=db, pk=pk, obj=param)
    return response_base.success(data=deduction_plan.id)


@router.delete("", summary="")
async def delete_deduction_plan(db: CurrentSessionTransaction, pks: list[int]) -> ResponseModel:
    """删除推演方案配置"""
    count = await deduction_plan_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()
