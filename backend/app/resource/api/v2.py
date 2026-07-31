import json
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Path, Query, Request, Response, UploadFile, status
from pydantic import ValidationError

from backend.app.resource.schema.resource import (
    AgentReplacementResult,
    CreateResourceParam,
    GetAgentVersionImpact,
    GetEnvironmentRuntime,
    GetResourceDetail,
    GetResourcePage,
)
from backend.app.resource.service.resource_service import resource_service
from backend.common.exception import errors
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter(prefix="/resources", tags=["资源配置 V2"])
ResourceIdPath = Annotated[str, Path(pattern=r"^[1-9]\d*$")]


def _download_url(request: Request, resource_id: str, version_id: str) -> str:
    return str(request.url_for("download_resource_version", resource_id=resource_id, version_id=version_id))


@router.get("", response_model=GetResourcePage, response_model_exclude_none=True)
async def get_resource_list(
    db: CurrentSession,
    type_filter: Annotated[
        Literal["all", "scenario", "strategy", "agent", "environment"], Query(alias="type")
    ] = "all",
    search: str = "",
    sort_by: Annotated[Literal["name", "type", "updatedAt"], Query(alias="sortBy")] = "updatedAt",
    sort_order: Annotated[Literal["asc", "desc"], Query(alias="sortOrder")] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=10_000)] = 8,
    include_archived: Annotated[bool, Query(alias="includeArchived")] = False,
    archived: bool | None = None,
) -> GetResourcePage:
    return await resource_service.get_list(
        db=db,
        resource_type=type_filter,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        include_archived=include_archived,
        archived=archived,
    )


@router.get("/{resource_id}", response_model=GetResourceDetail, response_model_exclude_none=True)
async def get_resource_by_id(
    request: Request,
    db: CurrentSession,
    resource_id: ResourceIdPath,
) -> GetResourceDetail:
    return await resource_service.get(
        db=db,
        pk=int(resource_id),
        download_url=lambda resource, version: _download_url(request, resource, version),
    )


@router.post("", response_model=GetResourceDetail, response_model_exclude_none=True)
async def create_resource(
    request: Request,
    db: CurrentSessionTransaction,
    metadata: Annotated[str, Form()],
    file: Annotated[UploadFile | None, File()] = None,
) -> GetResourceDetail:
    try:
        obj = CreateResourceParam.model_validate(json.loads(metadata))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise errors.HTTPError(code=422, msg=f"资源 metadata 无效：{exc}") from exc
    content = await file.read() if file else None
    return await resource_service.create(
        db=db,
        obj=obj,
        filename=file.filename if file else None,
        content=content,
        content_type=file.content_type if file else None,
        download_url=lambda resource, version: _download_url(request, resource, version),
    )


@router.post(
    "/{resource_id}/versions",
    response_model=GetResourceDetail | AgentReplacementResult,
    response_model_exclude_none=True,
)
async def create_resource_version(
    request: Request,
    db: CurrentSessionTransaction,
    resource_id: ResourceIdPath,
    file: Annotated[UploadFile, File()],
    version: Annotated[str | None, Form()] = None,
) -> GetResourceDetail | AgentReplacementResult:
    return await resource_service.add_version(
        db=db,
        pk=int(resource_id),
        requested_version=version,
        filename=file.filename or "resource.bin",
        content=await file.read(),
        content_type=file.content_type,
        download_url=lambda resource, version_id: _download_url(request, resource, version_id),
    )


@router.post("/{resource_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_agent_resource(db: CurrentSessionTransaction, resource_id: ResourceIdPath) -> Response:
    await resource_service.set_archived(db=db, pk=int(resource_id), archived=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{resource_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_agent_resource(db: CurrentSessionTransaction, resource_id: ResourceIdPath) -> Response:
    await resource_service.set_archived(db=db, pk=int(resource_id), archived=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(db: CurrentSessionTransaction, resource_id: ResourceIdPath) -> Response:
    await resource_service.delete(db=db, pk=int(resource_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{resource_id}/runtime", response_model=GetEnvironmentRuntime, response_model_exclude_none=True
)
async def get_environment_runtime(db: CurrentSession, resource_id: ResourceIdPath) -> GetEnvironmentRuntime:
    return await resource_service.get_environment_runtime(db=db, pk=int(resource_id))


@router.get(
    "/{resource_id}/versions/{version_id}/file",
    name="download_resource_version",
)
async def download_resource_version(
    db: CurrentSession,
    resource_id: ResourceIdPath,
    version_id: Annotated[str, Path(pattern=r"^[1-9]\d*$")],
) -> Response:
    filename, content, content_type = await resource_service.get_file(
        db=db,
        resource_id=int(resource_id),
        version_id=int(version_id),
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/{resource_id}/versions/{version_id}/branch-references",
    response_model=GetAgentVersionImpact,
    response_model_exclude_none=True,
)
async def get_agent_version_branch_references(
    db: CurrentSession,
    resource_id: ResourceIdPath,
    version_id: Annotated[str, Path(pattern=r"^[1-9]\d*$")],
) -> GetAgentVersionImpact:
    return await resource_service.get_agent_version_impact(
        db=db,
        resource_id=int(resource_id),
        version_id=int(version_id),
    )
