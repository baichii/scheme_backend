from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.branch_scheme.crud.branch_scheme import branch_scheme_revision_dao
from backend.app.branch_scheme.schema.branch_scheme import BranchSchemeGraph
from backend.app.configuration.service.configuration_service import configuration_service
from backend.app.deduction.crud.deduction import deduction_dao
from backend.app.deduction.schema.deduction import DeductionGraph
from backend.app.deduction_run.crud.deduction_run import (
    deduction_run_dao,
    deduction_runtime_message_dao,
    deduction_task_dao,
)
from backend.app.deduction_run.model.deduction_run import DeductionRun, DeductionTask
from backend.app.deduction_run.schema.deduction_run import (
    CreateDeductionRunParam,
    GetDeductionRunSnapshot,
    GetDeductionRunSummary,
    GetDeductionTask,
    GetEnvironmentRuntimeSnapshot,
    GetRuntimeEventPage,
    GetRuntimeLogPage,
    RuntimeEventMessage,
    RuntimeLogMessage,
    RuntimeRunStateMessage,
)
from backend.app.deduction_run.service.compiler import (
    PreparedAgent,
    PreparedBranch,
    compile_deduction_run,
)
from backend.app.resource.crud.resource import resource_dao, resource_version_dao
from backend.app.resource.service.resource_service import resource_service
from backend.common.exception import errors
from backend.utils.snowflake import snowflake
from backend.utils.timezone import timezone


def build_run_summary(run: DeductionRun) -> GetDeductionRunSummary:
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


def _build_task(task: DeductionTask) -> GetDeductionTask:
    return GetDeductionTask(
        id=str(task.id),
        kind=task.kind,
        parent_task_id=str(task.parent_task_id) if task.parent_task_id else None,
        source_node_id=task.source_node_id,
        branch_node_id=task.branch_node_id,
        branch_scheme_id=str(task.branch_scheme_id),
        branch_scheme_name=task.branch_scheme_name,
        name=task.name,
        agent_resource_id=str(task.agent_resource_id) if task.agent_resource_id else None,
        agent_version_id=str(task.agent_version_id) if task.agent_version_id else None,
        agent_revision_number=task.agent_revision_number,
        agent_checksum=task.agent_checksum,
        agent_name=task.agent_name,
        dependency_ids=[str(value) for value in task.dependency_ids],
        status=task.status,
        started_at=task.started_at,
        ended_at=task.ended_at,
    )


async def build_run_snapshot(db: AsyncSession, run: DeductionRun) -> GetDeductionRunSnapshot:
    tasks = await deduction_task_dao.get_by_run(db, run.id)
    return GetDeductionRunSnapshot(
        **build_run_summary(run).model_dump(),
        sequence=run.sequence,
        environment_runtime=GetEnvironmentRuntimeSnapshot.model_validate(run.environment_runtime),
        sim_time=run.sim_time,
        tasks=[_build_task(task) for task in tasks],
        branches=run.branches,
    )


class DeductionRunService:
    """推演运行创建、查询和停止服务。"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> GetDeductionRunSnapshot:
        run = await deduction_run_dao.get(db, pk)
        if not run:
            raise errors.NotFoundError(msg="推演运行不存在")
        return await build_run_snapshot(db, run)

    @staticmethod
    async def create(
        *,
        db: AsyncSession,
        obj: CreateDeductionRunParam,
        resource_base_url: str,
    ) -> GetDeductionRunSnapshot:
        deduction_id = int(obj.deduction_id)
        environment_id = int(obj.environment_resource_id)
        deduction = await deduction_dao.get(db, deduction_id)
        if not deduction:
            raise errors.NotFoundError(msg="推演方案不存在")
        if deduction.status != "ready":
            raise errors.ConflictError(msg="只有已就绪的推演方案可以启动")
        if await deduction_run_dao.get_active_by_deduction(db, deduction_id):
            raise errors.ConflictError(msg="该推演方案已有活动中的运行")

        environment = await resource_dao.get(db, environment_id)
        if not environment or environment.type != "environment" or not environment.environment:
            raise errors.HTTPError(code=422, msg="运行环境不存在")
        if environment.environment.get("scenarioTypeKey") != deduction.scenario_type_key:
            raise errors.HTTPError(code=422, msg="运行环境与推演想定类型不兼容")
        runtime = await resource_service.get_environment_runtime(db=db, pk=environment_id)
        if runtime.status != "connected":
            raise errors.HTTPError(code=422, msg="运行环境当前不可连接")
        template_key = environment.environment.get("template")
        environment_template = configuration_service.environment_documents.get(template_key)
        if not environment_template:
            raise errors.HTTPError(code=422, msg="运行环境模板不存在")

        graph = DeductionGraph.model_validate(deduction.graph)
        prepared_branches: list[PreparedBranch] = []
        for node in graph.nodes:
            if node.kind != "branch-scheme":
                continue
            revision = await branch_scheme_revision_dao.get(db, int(node.branch_scheme_revision_id))
            if (
                not revision
                or revision.branch_scheme_id != int(node.branch_scheme_id)
                or revision.status != "configured"
                or revision.scenario_type_key != deduction.scenario_type_key
            ):
                raise errors.HTTPError(code=422, msg=f"分支方案“{node.branch_scheme_name}”修订不可运行")
            branch_graph = BranchSchemeGraph.model_validate(revision.graph)
            agents: dict[str, PreparedAgent] = {}
            for branch_node in branch_graph.nodes:
                if branch_node.scope != "task" or not branch_node.agent_binding:
                    continue
                binding = branch_node.agent_binding
                resource = await resource_dao.get(db, int(binding.resource_id))
                version = await resource_version_dao.get(db, int(binding.agent_version_id))
                if (
                    not resource
                    or resource.type != "agent"
                    or not version
                    or version.resource_id != resource.id
                    or not version.file_name
                    or not version.object_key
                ):
                    raise errors.HTTPError(code=422, msg=f"智能体“{binding.resource_name}”固定版本不可用")
                agents[branch_node.id] = PreparedAgent(
                    node=branch_node,
                    resource=resource,
                    version=version,
                )
            prepared_branches.append(
                PreparedBranch(node=node, revision=revision, graph=branch_graph, agents=agents)
            )

        run_id = snowflake.generate()
        compiled = compile_deduction_run(
            run_id=run_id,
            deduction=deduction,
            graph=graph,
            environment=environment,
            environment_template=environment_template,
            branches=prepared_branches,
            resource_base_url=resource_base_url,
        )
        now = timezone.now()
        sim_time = (runtime.environment_time or now).isoformat()
        environment_runtime = {
            "status": "healthy",
            "checkedAt": now.isoformat(),
            "containerIp": environment.environment.get("values", {}).get("ip"),
            "containerPort": environment.environment.get("values", {}).get("port"),
        }
        try:
            run = await deduction_run_dao.create(
                db,
                {
                    "id": run_id,
                    "deduction_id": deduction.id,
                    "status": "starting",
                    "environment_resource_id": environment.id,
                    "environment_name": environment.name,
                    "environment_snapshot": environment.environment,
                    "environment_runtime": environment_runtime,
                    "branches": compiled.branches,
                    "engine_request": compiled.engine_request.model_dump(mode="json", by_alias=True),
                    "sim_time": sim_time,
                    "started_at": now,
                    "sequence": 1,
                },
            )
            await deduction_task_dao.create_many(db, compiled.task_values)
            message = RuntimeRunStateMessage(
                sequence=1,
                runId=str(run_id),
                emittedAt=now,
                simTime=sim_time,
                status="starting",
            )
            await deduction_runtime_message_dao.create(
                db,
                {
                    "run_id": run_id,
                    "sequence": 1,
                    "type": "run_state",
                    "payload": message.model_dump(mode="json", by_alias=True, exclude_none=True),
                    "emitted_at": now,
                },
            )
        except IntegrityError as exc:
            raise errors.ConflictError(msg="该推演方案已有活动中的运行") from exc
        return await build_run_snapshot(db, run)

    @staticmethod
    async def stop(*, db: AsyncSession, pk: int) -> GetDeductionRunSnapshot:
        run = await deduction_run_dao.get(db, pk, for_update=True)
        if not run:
            raise errors.NotFoundError(msg="推演运行不存在")
        if run.status in {"stopping", "stopped"}:
            return await build_run_snapshot(db, run)
        if run.status in {"finished", "failed"}:
            raise errors.ConflictError(msg="已结束的推演运行不能停止")
        now = timezone.now()
        sequence = run.sequence + 1
        message = RuntimeRunStateMessage(
            sequence=sequence,
            runId=str(run.id),
            emittedAt=now,
            simTime=run.sim_time,
            status="stopping",
        )
        run.status = "stopping"
        run.sequence = sequence
        await deduction_runtime_message_dao.create(
            db,
            {
                "run_id": run.id,
                "sequence": sequence,
                "type": "run_state",
                "payload": message.model_dump(mode="json", by_alias=True, exclude_none=True),
                "emitted_at": now,
            },
        )
        await db.flush()
        return await build_run_snapshot(db, run)

    @staticmethod
    async def get_events(
        *,
        db: AsyncSession,
        pk: int,
        before_sequence: int | None,
        limit: int,
        branch_node_id: str | None,
    ) -> GetRuntimeEventPage:
        if not await deduction_run_dao.get(db, pk):
            raise errors.NotFoundError(msg="推演运行不存在")
        rows = await deduction_runtime_message_dao.get_history(
            db,
            run_id=pk,
            message_type="event",
            before_sequence=before_sequence,
            limit=limit,
            branch_node_id=branch_node_id,
        )
        selected = rows[:limit]
        items = [RuntimeEventMessage.model_validate(row.payload) for row in reversed(selected)]
        return GetRuntimeEventPage(
            items=items,
            has_more=len(rows) > limit,
            next_before_sequence=items[0].sequence if len(rows) > limit and items else None,
        )

    @staticmethod
    async def get_logs(
        *,
        db: AsyncSession,
        pk: int,
        task_id: int,
        before_sequence: int | None,
        limit: int,
    ) -> GetRuntimeLogPage:
        if not await deduction_run_dao.get(db, pk):
            raise errors.NotFoundError(msg="推演运行不存在")
        task = await deduction_task_dao.get(db, task_id)
        if not task or task.run_id != pk or task.kind != "agent":
            raise errors.HTTPError(code=422, msg="请选择有效的智能体任务")
        rows = await deduction_runtime_message_dao.get_history(
            db,
            run_id=pk,
            message_type="log",
            before_sequence=before_sequence,
            limit=limit,
            task_id=task_id,
        )
        selected = rows[:limit]
        items = [RuntimeLogMessage.model_validate(row.payload) for row in reversed(selected)]
        return GetRuntimeLogPage(
            items=items,
            has_more=len(rows) > limit,
            next_before_sequence=items[0].sequence if len(rows) > limit and items else None,
        )


deduction_run_service: DeductionRunService = DeductionRunService()
