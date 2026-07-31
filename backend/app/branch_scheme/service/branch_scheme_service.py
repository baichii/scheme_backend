from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.branch_scheme.crud.branch_scheme import (
    branch_scheme_dao,
    branch_scheme_revision_dao,
)
from backend.app.branch_scheme.model.branch_scheme import BranchScheme, BranchSchemeRevision
from backend.app.branch_scheme.schema.branch_scheme import (
    BranchSchemeGraph,
    CreateBranchSchemeParam,
    CreateBranchSchemeRevisionParam,
    GetBranchSchemeDetail,
    GetBranchSchemePage,
    GetBranchSchemeRevision,
    GetBranchSchemeRevisionSummary,
    GetBranchSchemeSummary,
    UpdateBranchSchemeParam,
    get_default_branch_scheme_graph,
)
from backend.app.configuration.service.configuration_service import configuration_service
from backend.app.deduction.crud.deduction import deduction_dao
from backend.app.resource.crud.resource import resource_dao, resource_version_dao
from backend.app.resource.schema.protocol import AgentConfig
from backend.app.resource.service.validation import validate_agent_parameter_value
from backend.common.exception import errors
from backend.utils.snowflake import snowflake


class BranchSchemeService:
    """分支方案聚合与不可变修订服务。"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> GetBranchSchemeDetail:
        aggregate = await branch_scheme_dao.get(db, pk)
        if not aggregate:
            raise errors.NotFoundError(msg="分支方案不存在或已被删除")
        revision = await branch_scheme_revision_dao.get(db, aggregate.head_revision_id)
        if not revision:
            raise errors.ServerError(msg="分支方案当前修订不存在")
        return _build_detail(aggregate, revision)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        status: str,
        search: str,
        page: int,
        page_size: int,
        sort_order: str,
    ) -> GetBranchSchemePage:
        aggregates = await branch_scheme_dao.get_list(db)
        items: list[GetBranchSchemeSummary] = []
        normalized_search = search.strip().casefold()
        for aggregate in aggregates:
            revision_id = (
                aggregate.published_revision_id
                if status == "configured" and aggregate.published_revision_id
                else aggregate.head_revision_id
            )
            revision = await branch_scheme_revision_dao.get(db, revision_id)
            if not revision:
                continue
            if status == "configured" and not aggregate.published_revision_id:
                continue
            if status == "draft" and revision.status != "draft":
                continue
            if (
                normalized_search
                and normalized_search not in f"{revision.name} {revision.description}".casefold()
            ):
                continue
            items.append(_build_summary(aggregate, revision))
        items.sort(key=lambda item: item.updated_at, reverse=sort_order != "asc")
        total = len(items)
        return GetBranchSchemePage(
            items=items[(page - 1) * page_size : page * page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateBranchSchemeParam) -> GetBranchSchemeDetail:
        _validate_affiliation(obj.scenario_type_key, obj.side_key)
        if await branch_scheme_dao.get_by_name(db, obj.name):
            raise errors.ConflictError(msg="已存在同名分支方案")
        scheme_id = snowflake.generate()
        revision_id = snowflake.generate()
        graph = get_default_branch_scheme_graph()
        try:
            aggregate = await branch_scheme_dao.create(
                db,
                {
                    "id": scheme_id,
                    "normalized_name": obj.name.casefold(),
                    "head_revision_id": revision_id,
                    "head_revision_number": 1,
                    "created_by": "当前用户",
                },
            )
            revision = await branch_scheme_revision_dao.create(
                db,
                {
                    "id": revision_id,
                    "branch_scheme_id": scheme_id,
                    "revision_number": 1,
                    "name": obj.name,
                    "description": obj.description,
                    "scenario_type_key": obj.scenario_type_key,
                    "side_key": obj.side_key,
                    "status": "draft",
                    "graph": graph.model_dump(mode="json", by_alias=True, exclude_none=True),
                    "created_by": "当前用户",
                },
            )
        except IntegrityError as exc:
            raise errors.ConflictError(msg="已存在同名分支方案") from exc
        return _build_detail(aggregate, revision)

    @staticmethod
    async def create_revision(
        *,
        db: AsyncSession,
        pk: int,
        obj: CreateBranchSchemeRevisionParam,
    ) -> GetBranchSchemeRevision:
        aggregate = await branch_scheme_dao.get(db, pk)
        if not aggregate:
            raise errors.NotFoundError(msg="分支方案不存在或已被删除")
        if str(aggregate.head_revision_id) != obj.base_revision_id:
            raise errors.ConflictError(msg="分支方案已产生新版本，请重新载入后再保存")
        current = await branch_scheme_revision_dao.get(db, aggregate.head_revision_id)
        if not current:
            raise errors.ServerError(msg="分支方案当前修订不存在")
        name = obj.name if obj.name is not None else current.name
        description = obj.description if obj.description is not None else current.description
        status = obj.status if obj.status is not None else current.status
        graph = obj.graph if obj.graph is not None else BranchSchemeGraph.model_validate(current.graph)
        duplicate = await branch_scheme_dao.get_by_name(db, name)
        if duplicate and duplicate.id != pk:
            raise errors.ConflictError(msg="已存在同名分支方案")
        await _validate_graph_bindings(db, graph, status=status, base=current)
        revision_id = snowflake.generate()
        revision_number = aggregate.head_revision_number + 1
        values = {
            "normalized_name": name.casefold(),
            "head_revision_id": revision_id,
            "head_revision_number": revision_number,
        }
        if status == "configured":
            values.update(
                published_revision_id=revision_id,
                published_revision_number=revision_number,
            )
        if not await branch_scheme_dao.compare_and_swap_head(
            db,
            pk=pk,
            base_revision_id=aggregate.head_revision_id,
            values=values,
        ):
            raise errors.ConflictError(msg="分支方案已产生新版本，请重新载入后再保存")
        try:
            revision = await branch_scheme_revision_dao.create(
                db,
                {
                    "id": revision_id,
                    "branch_scheme_id": pk,
                    "revision_number": revision_number,
                    "parent_revision_id": current.id,
                    "name": name,
                    "description": description,
                    "scenario_type_key": current.scenario_type_key,
                    "side_key": current.side_key,
                    "status": status,
                    "graph": graph.model_dump(mode="json", by_alias=True, exclude_none=True),
                    "created_by": "当前用户",
                    "origin": None,
                },
            )
        except IntegrityError as exc:
            raise errors.ConflictError(msg="分支方案已产生新版本，请重新载入后再保存") from exc
        return _build_revision(revision)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateBranchSchemeParam,
    ) -> GetBranchSchemeDetail:
        aggregate = await branch_scheme_dao.get(db, pk)
        if not aggregate:
            raise errors.NotFoundError(msg="分支方案不存在或已被删除")
        await branch_scheme_service.create_revision(
            db=db,
            pk=pk,
            obj=CreateBranchSchemeRevisionParam(
                base_revision_id=str(aggregate.head_revision_id),
                **obj.model_dump(exclude_unset=True),
            ),
        )
        return await branch_scheme_service.get(db=db, pk=pk)

    @staticmethod
    async def get_revision(*, db: AsyncSession, pk: int, revision_id: int) -> GetBranchSchemeRevision:
        revision = await branch_scheme_revision_dao.get(db, revision_id)
        if not revision or revision.branch_scheme_id != pk:
            raise errors.NotFoundError(msg="分支方案版本不存在或已被删除")
        return _build_revision(revision)

    @staticmethod
    async def get_revision_list(*, db: AsyncSession, pk: int) -> list[GetBranchSchemeRevisionSummary]:
        if not await branch_scheme_dao.get(db, pk):
            raise errors.NotFoundError(msg="分支方案不存在或已被删除")
        return [
            GetBranchSchemeRevisionSummary(
                id=str(revision.id),
                branch_scheme_id=str(revision.branch_scheme_id),
                revision_number=revision.revision_number,
                parent_revision_id=str(revision.parent_revision_id)
                if revision.parent_revision_id
                else None,
                status=revision.status,
                created_by=revision.created_by,
                created_at=revision.create_at,
            )
            for revision in await branch_scheme_revision_dao.get_list(db, pk)
        ]

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> None:
        aggregate = await branch_scheme_dao.get(db, pk)
        if not aggregate:
            raise errors.NotFoundError(msg="分支方案不存在或已被删除")
        for deduction in await deduction_dao.get_all(db):
            if any(
                node.get("kind") == "branch-scheme" and str(node.get("branchSchemeId")) == str(pk)
                for node in deduction.graph.get("nodes", [])
            ):
                raise errors.ConflictError(msg=f"该分支方案仍被推演“{deduction.name}”引用，无法删除")
        await branch_scheme_dao.delete(db, pk)


async def _validate_graph_bindings(
    db: AsyncSession,
    graph: BranchSchemeGraph,
    *,
    status: str,
    base: BranchSchemeRevision,
) -> None:
    base_graph = BranchSchemeGraph.model_validate(base.graph)
    base_bindings = {
        node.id: node.agent_binding.agent_version_id for node in base_graph.nodes if node.agent_binding
    }
    for node in graph.nodes:
        if node.scope != "task":
            continue
        incoming = any(edge.target == node.id for edge in graph.edges)
        outgoing = any(edge.source == node.id for edge in graph.edges)
        if status == "configured" and (not incoming or not outgoing):
            raise errors.HTTPError(code=422, msg=f"“{node.name}”必须同时具有入线和出线")
        binding = node.agent_binding
        if not binding:
            if status == "configured":
                raise errors.HTTPError(code=422, msg=f"“{node.name}”尚未绑定智能体")
            continue
        try:
            resource_id = int(binding.resource_id)
            version_id = int(binding.agent_version_id)
        except ValueError as exc:
            raise errors.HTTPError(code=422, msg=f"“{node.name}”绑定的智能体 ID 无效") from exc
        resource = await resource_dao.get(db, resource_id)
        version = await resource_version_dao.get(db, version_id)
        if not resource or resource.type != "agent" or not version or version.resource_id != resource.id:
            raise errors.HTTPError(code=422, msg=f"“{node.name}”绑定的智能体修订不存在")
        if version.revision_number != binding.agent_revision_number:
            raise errors.HTTPError(code=422, msg=f"“{node.name}”的智能体修订号不匹配")
        if resource.archived and base_bindings.get(node.id) != binding.agent_version_id:
            raise errors.HTTPError(code=422, msg=f"“{node.name}”不能新绑定已归档智能体")
        config = AgentConfig.model_validate(version.parsed_data)
        expected = {parameter.name for parameter in config.PARAMS}
        if status == "configured" and set(binding.parameters) != expected:
            raise errors.HTTPError(code=422, msg=f"“{node.name}”的智能体参数不完整")
        for parameter in config.PARAMS:
            if parameter.name not in binding.parameters and status == "draft":
                continue
            if not validate_agent_parameter_value(parameter, binding.parameters.get(parameter.name)):
                raise errors.HTTPError(
                    code=422, msg=f"“{node.name}”的参数“{parameter.chineseName}”格式错误"
                )


def _validate_affiliation(scenario_type_key: str, side_key: str) -> None:
    scenario = configuration_service.scenario_documents.get(scenario_type_key)
    if not scenario:
        raise errors.HTTPError(code=422, msg=f"想定类型不存在：{scenario_type_key}")
    if side_key not in {side.key for side in scenario.sides}:
        raise errors.HTTPError(code=422, msg=f"阵营 {side_key} 不属于想定类型 {scenario.name}")


def _build_revision(revision: BranchSchemeRevision) -> GetBranchSchemeRevision:
    return GetBranchSchemeRevision(
        id=str(revision.id),
        branch_scheme_id=str(revision.branch_scheme_id),
        revision_number=revision.revision_number,
        parent_revision_id=str(revision.parent_revision_id) if revision.parent_revision_id else None,
        name=revision.name,
        description=revision.description,
        scenario_type_key=revision.scenario_type_key,
        side_key=revision.side_key,
        status=revision.status,
        created_by=revision.created_by,
        origin=revision.origin,
        graph=revision.graph,
        created_at=revision.create_at,
    )


def _build_detail(aggregate: BranchScheme, revision: BranchSchemeRevision) -> GetBranchSchemeDetail:
    return GetBranchSchemeDetail(
        id=str(aggregate.id),
        name=revision.name,
        description=revision.description,
        scenario_type_key=revision.scenario_type_key,
        side_key=revision.side_key,
        status=revision.status,
        created_by=aggregate.created_by,
        origin=revision.origin,
        graph=revision.graph,
        head_revision_id=str(aggregate.head_revision_id),
        head_revision_number=aggregate.head_revision_number,
        published_revision_id=str(aggregate.published_revision_id)
        if aggregate.published_revision_id
        else None,
        published_revision_number=aggregate.published_revision_number,
        created_at=aggregate.create_at,
        updated_at=aggregate.update_at or aggregate.create_at,
    )


def _build_summary(aggregate: BranchScheme, revision: BranchSchemeRevision) -> GetBranchSchemeSummary:
    graph = BranchSchemeGraph.model_validate(revision.graph)
    return GetBranchSchemeSummary(
        id=str(aggregate.id),
        name=revision.name,
        description=revision.description,
        scenario_type_key=revision.scenario_type_key,
        side_key=revision.side_key,
        status=revision.status,
        head_revision_id=str(aggregate.head_revision_id),
        head_revision_number=aggregate.head_revision_number,
        published_revision_id=str(aggregate.published_revision_id)
        if aggregate.published_revision_id
        else None,
        published_revision_number=aggregate.published_revision_number,
        has_draft=aggregate.head_revision_id != aggregate.published_revision_id,
        node_count=len(graph.nodes),
        created_by=aggregate.created_by,
        origin=revision.origin,
        updated_at=aggregate.update_at or aggregate.create_at,
    )


branch_scheme_service = BranchSchemeService()
