from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response, status

from backend.app.branch_scheme.schema.branch_scheme import (
    CreateBranchSchemeParam,
    CreateBranchSchemeRevisionParam,
    GetBranchSchemeDetail,
    GetBranchSchemePage,
    GetBranchSchemeRevision,
    GetBranchSchemeRevisionSummary,
    UpdateBranchSchemeParam,
)
from backend.app.branch_scheme.service.branch_scheme_service import branch_scheme_service
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter(prefix="/branch-schemes", tags=["分支方案 V2"])
BranchSchemeIdPath = Annotated[str, Path(pattern=r"^[1-9]\d*$")]


@router.get("", response_model=GetBranchSchemePage, response_model_exclude_none=True)
async def get_branch_scheme_list(
    db: CurrentSession,
    status_filter: Annotated[Literal["all", "draft", "configured"], Query(alias="status")] = "all",
    search: str = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 12,
    sort_order: Annotated[Literal["asc", "desc"], Query(alias="sortOrder")] = "desc",
) -> GetBranchSchemePage:
    return await branch_scheme_service.get_list(
        db=db,
        status=status_filter,
        search=search,
        page=page,
        page_size=page_size,
        sort_order=sort_order,
    )


@router.get("/{branch_scheme_id}", response_model=GetBranchSchemeDetail, response_model_exclude_none=True)
async def get_branch_scheme_by_id(
    db: CurrentSession,
    branch_scheme_id: BranchSchemeIdPath,
) -> GetBranchSchemeDetail:
    return await branch_scheme_service.get(db=db, pk=int(branch_scheme_id))


@router.post("", response_model=GetBranchSchemeDetail, response_model_exclude_none=True)
async def create_branch_scheme(
    db: CurrentSessionTransaction,
    obj: CreateBranchSchemeParam,
) -> GetBranchSchemeDetail:
    return await branch_scheme_service.create(db=db, obj=obj)


@router.put("/{branch_scheme_id}", response_model=GetBranchSchemeDetail, response_model_exclude_none=True)
async def update_branch_scheme(
    db: CurrentSessionTransaction,
    branch_scheme_id: BranchSchemeIdPath,
    obj: UpdateBranchSchemeParam,
) -> GetBranchSchemeDetail:
    return await branch_scheme_service.update(db=db, pk=int(branch_scheme_id), obj=obj)


@router.delete("/{branch_scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_scheme(
    db: CurrentSessionTransaction,
    branch_scheme_id: BranchSchemeIdPath,
) -> Response:
    await branch_scheme_service.delete(db=db, pk=int(branch_scheme_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{branch_scheme_id}/revisions",
    response_model=list[GetBranchSchemeRevisionSummary],
    response_model_exclude_none=True,
)
async def get_branch_scheme_revision_list(
    db: CurrentSession,
    branch_scheme_id: BranchSchemeIdPath,
) -> list[GetBranchSchemeRevisionSummary]:
    return await branch_scheme_service.get_revision_list(db=db, pk=int(branch_scheme_id))


@router.get(
    "/{branch_scheme_id}/revisions/{revision_id}",
    response_model=GetBranchSchemeRevision,
    response_model_exclude_none=True,
)
async def get_branch_scheme_revision_by_id(
    db: CurrentSession,
    branch_scheme_id: BranchSchemeIdPath,
    revision_id: Annotated[str, Path(pattern=r"^[1-9]\d*$")],
) -> GetBranchSchemeRevision:
    return await branch_scheme_service.get_revision(
        db=db,
        pk=int(branch_scheme_id),
        revision_id=int(revision_id),
    )


@router.post(
    "/{branch_scheme_id}/revisions",
    response_model=GetBranchSchemeRevision,
    response_model_exclude_none=True,
)
async def create_branch_scheme_revision(
    db: CurrentSessionTransaction,
    branch_scheme_id: BranchSchemeIdPath,
    obj: CreateBranchSchemeRevisionParam,
) -> GetBranchSchemeRevision:
    return await branch_scheme_service.create_revision(db=db, pk=int(branch_scheme_id), obj=obj)
