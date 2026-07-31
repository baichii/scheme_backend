import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, Path, Query, Request
from fastapi.responses import StreamingResponse

from backend.app.deduction_run.schema.deduction_run import (
    CreateDeductionRunParam,
    GetDeductionRunSnapshot,
    GetRuntimeEventPage,
    GetRuntimeLogPage,
)
from backend.app.deduction_run.service.coordinator import DeductionRunCoordinator
from backend.app.deduction_run.service.deduction_run_service import deduction_run_service
from backend.common.exception import errors
from backend.database.db import CurrentSession

router = APIRouter(prefix="/deduction-runs", tags=["推演运行 V2"])
RunIdPath = Annotated[str, Path(pattern=r"^[1-9]\d*$")]
TaskIdQuery = Annotated[str, Query(alias="taskId", pattern=r"^[1-9]\d*$")]


def _coordinator(request: Request) -> DeductionRunCoordinator:
    coordinator = getattr(request.app.state, "deduction_run_coordinator", None)
    if coordinator is None:
        raise errors.ServerError(msg="推演运行协调器尚未初始化")
    return coordinator


@router.post("", response_model=GetDeductionRunSnapshot, response_model_exclude_none=True)
async def create_deduction_run(
    request: Request,
    background_tasks: BackgroundTasks,
    db: CurrentSession,
    obj: CreateDeductionRunParam,
) -> GetDeductionRunSnapshot:
    try:
        snapshot = await deduction_run_service.create(
            db=db,
            obj=obj,
            resource_base_url=str(request.base_url).rstrip("/"),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    background_tasks.add_task(_coordinator(request).start_run, int(snapshot.id))
    return snapshot


@router.get("/{run_id}", response_model=GetDeductionRunSnapshot, response_model_exclude_none=True)
async def get_deduction_run_by_id(
    db: CurrentSession,
    run_id: RunIdPath,
) -> GetDeductionRunSnapshot:
    return await deduction_run_service.get(db=db, pk=int(run_id))


@router.post("/{run_id}/stop", response_model=GetDeductionRunSnapshot, response_model_exclude_none=True)
async def stop_deduction_run(
    request: Request,
    background_tasks: BackgroundTasks,
    db: CurrentSession,
    run_id: RunIdPath,
) -> GetDeductionRunSnapshot:
    try:
        snapshot = await deduction_run_service.stop(db=db, pk=int(run_id))
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    background_tasks.add_task(_coordinator(request).stop_run, int(run_id))
    return snapshot


@router.get("/{run_id}/events", response_model=GetRuntimeEventPage, response_model_exclude_none=True)
async def get_deduction_run_events(
    db: CurrentSession,
    run_id: RunIdPath,
    branch_node_id: Annotated[str | None, Query(alias="branchNodeId")] = None,
    before_sequence: Annotated[int | None, Query(alias="beforeSequence", ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> GetRuntimeEventPage:
    return await deduction_run_service.get_events(
        db=db,
        pk=int(run_id),
        before_sequence=before_sequence,
        limit=limit,
        branch_node_id=branch_node_id,
    )


@router.get("/{run_id}/logs", response_model=GetRuntimeLogPage, response_model_exclude_none=True)
async def get_deduction_run_logs(
    db: CurrentSession,
    run_id: RunIdPath,
    task_id: TaskIdQuery,
    before_sequence: Annotated[int | None, Query(alias="beforeSequence", ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> GetRuntimeLogPage:
    return await deduction_run_service.get_logs(
        db=db,
        pk=int(run_id),
        task_id=int(task_id),
        before_sequence=before_sequence,
        limit=limit,
    )


@router.get("/{run_id}/stream")
async def stream_deduction_run(
    request: Request,
    db: CurrentSession,
    run_id: RunIdPath,
    after_sequence: Annotated[int, Query(alias="afterSequence", ge=0)] = 0,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    await deduction_run_service.get(db=db, pk=int(run_id))
    cursor = after_sequence
    if last_event_id:
        try:
            cursor = max(cursor, int(last_event_id))
        except ValueError as exc:
            raise errors.HTTPError(code=422, msg="Last-Event-ID 必须是整数") from exc
    coordinator = _coordinator(request)

    async def generate():
        async for message in coordinator.iter_messages(int(run_id), cursor):
            if await request.is_disconnected():
                return
            if message is None:
                yield ": heartbeat\n\n"
                continue
            payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
            yield f"id: {message['sequence']}\ndata: {payload}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
