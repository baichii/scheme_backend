from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.branch_scheme.crud.branch_scheme import (
    branch_scheme_dao,
    branch_scheme_revision_dao,
)
from backend.app.deduction.crud.deduction import deduction_dao
from backend.app.deduction.model.deduction import Deduction
from backend.app.deduction.schema.deduction import (
    CreateDeductionInternal,
    CreateDeductionParam,
    DeductionGraph,
    GetDeductionDetail,
    GetDeductionListParam,
    GetDeductionPage,
    GetDeductionSummary,
    UpdateDeductionParam,
    get_default_deduction_graph,
    validate_ready_deduction_graph,
)
from backend.app.deduction_run.crud.deduction_run import deduction_run_dao
from backend.app.deduction_run.model.deduction_run import DeductionRun
from backend.app.deduction_run.schema.deduction_run import GetDeductionRunSummary
from backend.common.exception import errors


def _get_graph(deduction: Deduction) -> DeductionGraph:
    return DeductionGraph.model_validate(deduction.graph)


def _build_latest_run(run: DeductionRun | None) -> GetDeductionRunSummary | None:
    if run is None:
        return None
    return GetDeductionRunSummary(
        id=str(run.id),
        deduction_id=str(run.deduction_id),
        status=run.status,
        environment_resource_id=str(run.environment_resource_id),
        environment_name=run.environment_name,
        started_at=run.started_at,
        updated_at=run.update_at or run.create_at,
        ended_at=run.ended_at,
    )


def _build_detail(deduction: Deduction, latest_run: DeductionRun | None = None) -> GetDeductionDetail:
    return GetDeductionDetail(
        id=str(deduction.id),
        name=deduction.name,
        description=deduction.description,
        scenario_type_key=deduction.scenario_type_key,
        status=deduction.status,
        graph=_get_graph(deduction),
        created_by=deduction.created_by,
        created_at=deduction.create_at,
        updated_at=deduction.update_at or deduction.create_at,
        latest_run=_build_latest_run(latest_run),
    )


def _build_summary(deduction: Deduction, latest_run: DeductionRun | None = None) -> GetDeductionSummary:
    graph = _get_graph(deduction)
    return GetDeductionSummary(
        id=str(deduction.id),
        name=deduction.name,
        description=deduction.description,
        scenario_type_key=deduction.scenario_type_key,
        status=deduction.status,
        branch_scheme_count=sum(node.kind == "branch-scheme" for node in graph.nodes),
        created_by=deduction.created_by,
        updated_at=deduction.update_at or deduction.create_at,
        latest_run=_build_latest_run(latest_run),
    )


async def _validate_and_normalize_branch_references(
    db: AsyncSession,
    graph: DeductionGraph,
    *,
    deduction_status: str,
    scenario_type_key: str,
) -> DeductionGraph:
    for node in graph.nodes:
        if node.kind != "branch-scheme":
            continue
        try:
            branch_scheme_id = int(node.branch_scheme_id)
            revision_id = int(node.branch_scheme_revision_id)
        except ValueError as exc:
            raise errors.HTTPError(
                code=422, msg=f"分支方案“{node.branch_scheme_name}”引用 ID 无效"
            ) from exc
        aggregate = await branch_scheme_dao.get(db, branch_scheme_id)
        revision = await branch_scheme_revision_dao.get(db, revision_id)
        if not aggregate or not revision or revision.branch_scheme_id != aggregate.id:
            raise errors.HTTPError(code=422, msg=f"分支方案“{node.branch_scheme_name}”引用的修订不存在")
        if deduction_status == "ready":
            if revision.status != "configured":
                raise errors.HTTPError(code=422, msg=f"分支方案“{revision.name}”尚未配置完成")
            if revision.scenario_type_key != scenario_type_key:
                raise errors.HTTPError(code=422, msg=f"分支方案“{revision.name}”与推演想定类型不一致")
        node.branch_scheme_name = revision.name
        node.revision_number = revision.revision_number
    return graph


class DeductionService:
    """推演方案服务类。"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> GetDeductionDetail:
        """获取推演方案详情。"""

        deduction = await deduction_dao.get(db, pk)
        if not deduction:
            raise errors.NotFoundError(msg="推演方案不存在")
        latest = await deduction_run_dao.get_latest_by_deduction_ids(db, [deduction.id])
        return _build_detail(deduction, latest.get(deduction.id))

    @staticmethod
    async def get_list(*, db: AsyncSession, obj: GetDeductionListParam) -> GetDeductionPage:
        """获取推演方案分页列表。"""

        deductions, total = await deduction_dao.get_list(
            db,
            status=obj.status,
            search=obj.search,
            page=obj.page,
            page_size=obj.page_size,
            sort_order=obj.sort_order,
            run_status=obj.run_status,
        )
        latest = await deduction_run_dao.get_latest_by_deduction_ids(
            db, [deduction.id for deduction in deductions]
        )
        return GetDeductionPage(
            items=[_build_summary(deduction, latest.get(deduction.id)) for deduction in deductions],
            total=total,
            page=obj.page,
            page_size=obj.page_size,
        )

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateDeductionParam) -> GetDeductionDetail:
        """创建推演方案。"""

        if await deduction_dao.get_by_name(db, obj.name):
            raise errors.ConflictError(msg="推演方案名称已存在")

        graph = get_default_deduction_graph()
        internal = CreateDeductionInternal(
            name=obj.name,
            normalized_name=obj.name.casefold(),
            description=obj.description,
            scenario_type_key=obj.scenario_type_key,
            status="draft",
            graph=graph.model_dump(by_alias=True, exclude_none=True),
            created_by="当前用户",
        )
        try:
            deduction = await deduction_dao.create(db, internal)
        except IntegrityError as exc:
            raise errors.ConflictError(msg="推演方案名称已存在") from exc
        return _build_detail(deduction)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateDeductionParam,
    ) -> GetDeductionDetail:
        """更新推演方案。"""

        deduction = await deduction_dao.get(db, pk)
        if not deduction:
            raise errors.NotFoundError(msg="推演方案不存在")
        if await deduction_run_dao.get_active_by_deduction(db, pk):
            raise errors.ConflictError(msg="运行中的推演方案不能修改")

        name = obj.name if "name" in obj.model_fields_set else deduction.name
        description = obj.description if "description" in obj.model_fields_set else deduction.description
        deduction_status = obj.status if "status" in obj.model_fields_set else deduction.status
        graph = obj.graph if "graph" in obj.model_fields_set else _get_graph(deduction)
        graph = await _validate_and_normalize_branch_references(
            db,
            graph,
            deduction_status=deduction_status,
            scenario_type_key=deduction.scenario_type_key,
        )
        if deduction_status == "ready":
            try:
                validate_ready_deduction_graph(graph)
            except ValueError as exc:
                raise errors.HTTPError(code=422, msg=str(exc)) from exc

        duplicate = await deduction_dao.get_by_name(db, name)
        if duplicate and duplicate.id != deduction.id:
            raise errors.ConflictError(msg="推演方案名称已存在")

        values = {
            "name": name,
            "normalized_name": name.casefold(),
            "description": description,
            "status": deduction_status,
            "graph": graph.model_dump(by_alias=True, exclude_none=True),
        }
        try:
            await deduction_dao.update(db, pk, values)
        except IntegrityError as exc:
            raise errors.ConflictError(msg="推演方案名称已存在") from exc
        return await deduction_service.get(db=db, pk=pk)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """删除推演方案。"""

        deduction = await deduction_dao.get(db, pk)
        if not deduction:
            raise errors.NotFoundError(msg="推演方案不存在")
        if await deduction_run_dao.get_active_by_deduction(db, pk):
            raise errors.ConflictError(msg="运行中的推演方案不能删除")
        return await deduction_dao.delete(db, pk)


deduction_service: DeductionService = DeductionService()
