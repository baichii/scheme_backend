from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response, status

from backend.app.deduction.schema.deduction import (
    CreateDeductionParam,
    DeductionRunStatus,
    DeductionStatus,
    GetDeductionDetail,
    GetDeductionListParam,
    GetDeductionPage,
    UpdateDeductionParam,
)
from backend.app.deduction.service.deduction_service import deduction_service
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter(prefix="/deductions", tags=["推演管理 V2"])
DeductionIdPath = Annotated[str, Path(pattern=r"^[1-9]\d*$")]


@router.get("", response_model=GetDeductionPage, response_model_exclude_none=True)
async def get_deduction_list(
    db: CurrentSession,
    status_filter: Annotated[DeductionStatus | Literal["all"], Query(alias="status")] = "all",
    run_status: Annotated[DeductionRunStatus | Literal["all"], Query(alias="runStatus")] = "all",
    search: str = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 12,
    sort_order: Annotated[Literal["asc", "desc"], Query(alias="sortOrder")] = "desc",
) -> GetDeductionPage:
    """获取推演方案分页列表。"""

    obj = GetDeductionListParam(
        status=status_filter,
        run_status=run_status,
        search=search,
        page=page,
        page_size=page_size,
        sort_order=sort_order,
    )
    return await deduction_service.get_list(db=db, obj=obj)


@router.get(
    "/{deduction_id}",
    response_model=GetDeductionDetail,
    response_model_exclude_none=True,
)
async def get_deduction_by_id(db: CurrentSession, deduction_id: DeductionIdPath) -> GetDeductionDetail:
    """获取推演方案详情。"""

    return await deduction_service.get(db=db, pk=int(deduction_id))


@router.post("", response_model=GetDeductionDetail, response_model_exclude_none=True)
async def create_deduction(db: CurrentSessionTransaction, obj: CreateDeductionParam) -> GetDeductionDetail:
    """创建推演方案。"""

    return await deduction_service.create(db=db, obj=obj)


@router.put(
    "/{deduction_id}",
    response_model=GetDeductionDetail,
    response_model_exclude_none=True,
)
async def update_deduction(
    db: CurrentSessionTransaction,
    deduction_id: DeductionIdPath,
    obj: UpdateDeductionParam,
) -> GetDeductionDetail:
    """更新推演方案。"""

    return await deduction_service.update(db=db, pk=int(deduction_id), obj=obj)


@router.delete("/{deduction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deduction(db: CurrentSessionTransaction, deduction_id: DeductionIdPath) -> Response:
    """删除推演方案。"""

    await deduction_service.delete(db=db, pk=int(deduction_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
