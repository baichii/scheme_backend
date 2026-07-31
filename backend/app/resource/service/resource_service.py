import json
import mimetypes
from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.branch_scheme.crud.branch_scheme import (
    branch_scheme_dao,
    branch_scheme_revision_dao,
)
from backend.app.branch_scheme.schema.branch_scheme import BranchSchemeGraph
from backend.app.configuration.service.configuration_service import configuration_service
from backend.app.resource.crud.resource import resource_dao, resource_version_dao
from backend.app.resource.model.resource import Resource, ResourceVersion
from backend.app.resource.schema.protocol import AgentConfig, AgentParameter
from backend.app.resource.schema.resource import (
    AgentBranchReference,
    AgentReplacementResult,
    CreateResourceParam,
    EnvironmentConfig,
    GetAgentVersionImpact,
    GetEnvironmentRuntime,
    GetResourceDetail,
    GetResourcePage,
    GetResourceSummary,
    ResourceVersionDetail,
    ValidationReport,
)
from backend.app.resource.service.validation import validate_resource_file
from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.storage import ObjectStorageClient, get_object_storage
from backend.utils.snowflake import snowflake
from backend.utils.timezone import timezone

DownloadUrlBuilder = Callable[[str, str], str]


def _not_found(message: str) -> errors.NotFoundError:
    return errors.NotFoundError(msg=message)


def _agent_parameter_contract(parameter: AgentParameter) -> dict[str, Any]:
    value = parameter.model_dump(mode="json")
    value.pop("defaultValue", None)
    return value


def _compare_agent_versions(current: AgentConfig, target: AgentConfig) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if current.STATUS != target.STATUS:
        reasons.append("智能体状态定义发生变化")
    current_by_name = {parameter.name: parameter for parameter in current.PARAMS}
    target_by_name = {parameter.name: parameter for parameter in target.PARAMS}
    for parameter in current.PARAMS:
        replacement = target_by_name.get(parameter.name)
        if replacement is None:
            reasons.append(f"参数“{parameter.chineseName}”已删除或重命名")
        elif json.dumps(
            _agent_parameter_contract(parameter), sort_keys=True, ensure_ascii=False
        ) != json.dumps(_agent_parameter_contract(replacement), sort_keys=True, ensure_ascii=False):
            reasons.append(f"参数“{parameter.chineseName}”定义发生变化")
    additions = [parameter for parameter in target.PARAMS if parameter.name not in current_by_name]
    for parameter in additions:
        if parameter.required and parameter.defaultValue is None:
            reasons.append(f"新增必填参数“{parameter.chineseName}”没有默认值")
    if reasons:
        return "review", reasons
    if additions:
        return "defaults", [f"新增 {len(additions)} 个可使用默认值的参数"]
    return "direct", []


class ResourceService:
    """资源及不可变版本服务。"""

    def __init__(self, storage: ObjectStorageClient) -> None:
        self.storage = storage

    async def get(
        self,
        *,
        db: AsyncSession,
        pk: int,
        download_url: DownloadUrlBuilder,
    ) -> GetResourceDetail:
        resource = await resource_dao.get(db, pk)
        if not resource:
            raise _not_found("资源不存在")
        versions = await resource_version_dao.get_list(db, pk)
        return self._build_detail(resource, versions, download_url)

    async def get_list(
        self,
        *,
        db: AsyncSession,
        resource_type: str,
        search: str,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        include_archived: bool,
        archived: bool | None,
    ) -> GetResourcePage:
        rows = await resource_dao.get_list(db)
        if not include_archived:
            rows = [row for row in rows if not row.archived]
        if archived is not None:
            rows = [row for row in rows if row.archived is archived]
        if resource_type != "all":
            rows = [row for row in rows if row.type == resource_type]
        normalized_search = search.strip().casefold()
        if normalized_search:
            rows = [row for row in rows if normalized_search in row.name.casefold()]
        reverse = sort_order != "asc"
        key = {
            "name": lambda row: row.name.casefold(),
            "type": lambda row: row.type,
            "updatedAt": lambda row: row.update_at or row.create_at,
        }[sort_by]
        rows.sort(key=key, reverse=reverse)
        total = len(rows)
        rows = rows[(page - 1) * page_size : page * page_size]
        items = []
        for row in rows:
            versions = await resource_version_dao.get_list(db, row.id)
            items.append(self._build_summary(row, versions))
        return GetResourcePage(items=items, total=total, page=page, page_size=page_size)

    async def create(
        self,
        *,
        db: AsyncSession,
        obj: CreateResourceParam,
        filename: str | None,
        content: bytes | None,
        content_type: str | None,
        download_url: DownloadUrlBuilder,
    ) -> GetResourceDetail:
        resource_id = await resource_dao.next_agent_id(db) if obj.type == "agent" else snowflake.generate()
        version_id = snowflake.generate()
        name = obj.name.strip()
        description = obj.description.strip() if obj.description and obj.description.strip() else None
        uploaded_key: str | None = None

        if obj.type == "environment":
            if not name or obj.environment is None:
                raise errors.HTTPError(code=422, msg="环境名称和配置不能为空")
            environment, validation = self._validate_environment(obj.environment)
            version_values = {
                "id": version_id,
                "resource_id": resource_id,
                "version": "v1.0",
                "format": "ENV",
                "validation": validation.model_dump(mode="json", by_alias=True),
                "parsed_data": environment.model_dump(mode="json", by_alias=True),
            }
        else:
            if not filename or content is None:
                raise errors.HTTPError(code=422, msg="文件不能为空")
            scenario_names = await self._get_scenario_names(db)
            validated = validate_resource_file(obj.type, filename, content, scenario_names)
            if obj.type == "scenario":
                name = str(validated.parsed_data["name"]).strip()
            if not name:
                raise errors.HTTPError(code=422, msg="资源名称不能为空")
            if obj.type == "agent":
                revision_number = 1
                version = "R1"
                package_version = str(validated.parsed_data["VERSION"])
            else:
                revision_number = None
                version = self._normalize_semantic_version(obj.version)
                package_version = None
            uploaded_key = f"resources/{resource_id}/versions/{version_id}/{filename}"
            await self.storage.put(
                uploaded_key,
                content,
                content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            )
            version_values = {
                "id": version_id,
                "resource_id": resource_id,
                "version": version,
                "revision_number": revision_number,
                "package_version": package_version,
                "format": validated.format,
                "file_name": filename,
                "size": len(content),
                "checksum": validated.checksum,
                "object_key": uploaded_key,
                "parsed_data": validated.parsed_data,
                "validation": validated.report.model_dump(mode="json", by_alias=True),
            }

        if await resource_dao.get_by_name(db, resource_type=obj.type, name=name):
            if uploaded_key:
                await self._delete_object(uploaded_key)
            raise errors.ConflictError(msg="同类型资源名称已存在，请使用替换操作")
        try:
            resource = await resource_dao.create(
                db,
                {
                    "id": resource_id,
                    "type": obj.type,
                    "name": name,
                    "normalized_name": name.casefold(),
                    "description": description,
                    "current_version_id": version_id,
                    "archived": False,
                    "environment": obj.environment.model_dump(mode="json", by_alias=True)
                    if obj.environment
                    else None,
                },
            )
            version_row = await resource_version_dao.create(db, version_values)
        except Exception as exc:
            if uploaded_key:
                await self._delete_object(uploaded_key)
            if isinstance(exc, IntegrityError):
                raise errors.ConflictError(msg="资源名称或版本已存在") from exc
            raise
        return self._build_detail(resource, [version_row], download_url)

    async def add_version(
        self,
        *,
        db: AsyncSession,
        pk: int,
        requested_version: str | None,
        filename: str,
        content: bytes,
        content_type: str | None,
        download_url: DownloadUrlBuilder,
    ) -> GetResourceDetail | AgentReplacementResult:
        resource = await resource_dao.get(db, pk)
        if not resource:
            raise _not_found("资源不存在")
        if resource.type == "environment":
            raise errors.HTTPError(code=422, msg="环境资源不支持文件版本")
        if resource.type == "agent" and resource.archived:
            raise errors.HTTPError(code=422, msg="已归档智能体需恢复后才能替换")
        validated = validate_resource_file(
            resource.type, filename, content, await self._get_scenario_names(db)
        )
        versions = await resource_version_dao.get_list(db, pk)
        current = self._current_version(resource, versions)
        if resource.type == "agent":
            if await resource_version_dao.get_by_checksum(db, pk, validated.checksum):
                raise errors.ConflictError(msg="该 ZIP 与已有智能体修订完全相同")
            revision_number = max((version.revision_number or 0 for version in versions), default=0) + 1
            version_name = f"R{revision_number}"
            package_version = str(validated.parsed_data["VERSION"])
        else:
            revision_number = None
            version_name = self._normalize_semantic_version(requested_version)
            package_version = None
            if await resource_version_dao.get_by_version(db, pk, version_name):
                raise errors.ConflictError(msg="该版本号已存在")
            if resource.type == "scenario" and validated.parsed_data["name"] != resource.name:
                raise errors.HTTPError(code=422, msg="想定新版本的名称必须与当前资源一致")
        version_id = snowflake.generate()
        object_key = f"resources/{pk}/versions/{version_id}/{filename}"
        await self.storage.put(
            object_key,
            content,
            content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        )
        try:
            version_row = await resource_version_dao.create(
                db,
                {
                    "id": version_id,
                    "resource_id": pk,
                    "version": version_name,
                    "revision_number": revision_number,
                    "package_version": package_version,
                    "format": validated.format,
                    "file_name": filename,
                    "size": len(content),
                    "checksum": validated.checksum,
                    "object_key": object_key,
                    "parsed_data": validated.parsed_data,
                    "validation": validated.report.model_dump(mode="json", by_alias=True),
                },
            )
            await resource_dao.update(db, pk, {"current_version_id": version_id})
        except Exception as exc:
            await self._delete_object(object_key)
            if isinstance(exc, IntegrityError):
                raise errors.ConflictError(msg="资源版本已存在") from exc
            raise
        resource.current_version_id = version_id
        versions = [version_row, *versions]
        detail = self._build_detail(resource, versions, download_url)
        if resource.type != "agent":
            return detail
        impact = await self.get_agent_version_impact(
            db=db,
            resource_id=resource.id,
            version_id=version_row.id,
        )
        return AgentReplacementResult(
            resource=detail,
            version=self._build_version(version_row, download_url),
            package_version_unchanged=current.package_version == version_row.package_version,
            impact=impact,
        )

    async def get_agent_version_impact(
        self,
        *,
        db: AsyncSession,
        resource_id: int,
        version_id: int,
    ) -> GetAgentVersionImpact:
        resource = await resource_dao.get(db, resource_id)
        target = await resource_version_dao.get(db, version_id)
        if not resource or resource.type != "agent":
            raise _not_found("智能体资源不存在")
        if not target or target.resource_id != resource.id or target.revision_number is None:
            raise _not_found("目标智能体修订不存在")

        versions = await resource_version_dao.get_list(db, resource.id)
        version_by_id = {version.id: version for version in versions}
        target_config = AgentConfig.model_validate(target.parsed_data)
        aggregates = await branch_scheme_dao.get_list(db)
        references: list[AgentBranchReference] = []
        current_revision_ids = {aggregate.head_revision_id for aggregate in aggregates}

        priority = {"current": 0, "direct": 1, "defaults": 2, "review": 3, "draft-conflict": 4}
        for aggregate in aggregates:
            revision = await branch_scheme_revision_dao.get(db, aggregate.head_revision_id)
            if not revision:
                continue
            graph = BranchSchemeGraph.model_validate(revision.graph)
            nodes = [
                node
                for node in graph.nodes
                if node.agent_binding and node.agent_binding.resource_id == str(resource.id)
            ]
            if not nodes:
                continue
            current_ids = list(
                dict.fromkeys(
                    int(node.agent_binding.agent_version_id) for node in nodes if node.agent_binding
                )
            )
            current_versions = [version_by_id[value] for value in current_ids if value in version_by_id]
            if not current_versions:
                continue
            impact = "current" if all(version.id == target.id for version in current_versions) else "direct"
            reasons: list[str] = []
            if impact != "current":
                for current in current_versions:
                    comparison, comparison_reasons = _compare_agent_versions(
                        AgentConfig.model_validate(current.parsed_data),
                        target_config,
                    )
                    if priority[comparison] > priority[impact]:
                        impact = comparison
                    reasons.extend(comparison_reasons)
                if (
                    aggregate.published_revision_id
                    and aggregate.head_revision_id != aggregate.published_revision_id
                ):
                    impact = "draft-conflict"
                    reasons.insert(0, "分支方案已有未发布草稿")
            references.append(
                AgentBranchReference(
                    branch_scheme_id=str(aggregate.id),
                    branch_scheme_name=revision.name,
                    branch_status=revision.status,
                    base_revision_id=str(revision.id),
                    base_revision_number=revision.revision_number,
                    published_revision_id=(
                        str(aggregate.published_revision_id) if aggregate.published_revision_id else None
                    ),
                    current_agent_version_id=str(current_versions[0].id),
                    current_agent_revision_number=current_versions[0].revision_number or 1,
                    target_agent_version_id=str(target.id),
                    target_agent_revision_number=target.revision_number,
                    node_ids=[node.id for node in nodes],
                    impact=impact,
                    reasons=list(dict.fromkeys(reasons)),
                )
            )

        historical_reference_count = 0
        for revision in await branch_scheme_revision_dao.get_all(db):
            if revision.id in current_revision_ids:
                continue
            graph = BranchSchemeGraph.model_validate(revision.graph)
            if any(
                node.agent_binding and node.agent_binding.resource_id == str(resource.id)
                for node in graph.nodes
            ):
                historical_reference_count += 1
        return GetAgentVersionImpact(
            resource_id=str(resource.id),
            resource_name=resource.name,
            target_version_id=str(target.id),
            target_revision_number=target.revision_number,
            references=references,
            historical_reference_count=historical_reference_count,
        )

    async def set_archived(self, *, db: AsyncSession, pk: int, archived: bool) -> None:
        resource = await resource_dao.get(db, pk)
        if not resource or resource.type != "agent":
            raise _not_found("智能体资源不存在")
        await resource_dao.update(db, pk, {"archived": archived})

    async def delete(self, *, db: AsyncSession, pk: int) -> None:
        resource = await resource_dao.get(db, pk)
        if not resource:
            raise _not_found("资源不存在")
        if resource.type == "agent":
            await resource_dao.update(db, pk, {"archived": True})
            return
        versions = await resource_version_dao.get_list(db, pk)
        await resource_dao.delete(db, pk)
        for version in versions:
            if version.object_key:
                await self._delete_object(version.object_key)

    async def get_file(
        self, *, db: AsyncSession, resource_id: int, version_id: int
    ) -> tuple[str, bytes, str]:
        version = await resource_version_dao.get(db, version_id)
        if (
            not version
            or version.resource_id != resource_id
            or not version.object_key
            or not version.file_name
        ):
            raise _not_found("资源文件不存在")
        content = await self.storage.get(version.object_key)
        content_type = mimetypes.guess_type(version.file_name)[0] or "application/octet-stream"
        return version.file_name, content, content_type

    async def get_environment_runtime(self, *, db: AsyncSession, pk: int) -> GetEnvironmentRuntime:
        resource = await resource_dao.get(db, pk)
        if not resource or resource.type != "environment" or not resource.environment:
            raise _not_found("环境资源不存在")
        if settings.ENGINE_CLIENT_MODE != "fake":
            raise errors.HTTPError(code=501, msg="Matrix 环境运行态尚未实现")
        port = resource.environment.get("values", {}).get("port")
        if not isinstance(port, int):
            raise errors.HTTPError(code=422, msg="环境模板未提供数值端口")
        if port % 11 == 0:
            return GetEnvironmentRuntime(status="error")
        if port % 2 != 0:
            return GetEnvironmentRuntime(status="disconnected")
        return GetEnvironmentRuntime(status="connected", environment_time=timezone.now())

    async def _get_scenario_names(self, db: AsyncSession) -> set[str]:
        rows = await resource_dao.get_list(db)
        return {value for row in rows if row.type == "scenario" for value in (str(row.id), row.name)}

    @staticmethod
    def _normalize_semantic_version(version: str | None) -> str:
        if not version:
            raise errors.HTTPError(code=422, msg="版本号不能为空")
        normalized = version.strip()
        if normalized.startswith("v"):
            normalized = normalized[1:]
        parts = normalized.split(".")
        if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
            raise errors.HTTPError(code=422, msg="版本号必须是语义版本")
        return f"v{normalized}"

    @staticmethod
    def _validate_environment(obj: EnvironmentConfig) -> tuple[EnvironmentConfig, ValidationReport]:
        template = configuration_service.environment_documents.get(obj.template)
        scenario = configuration_service.scenario_documents.get(obj.scenario_type_key)
        if not template:
            raise errors.HTTPError(code=422, msg=f"环境模板不存在：{obj.template}")
        if not scenario:
            raise errors.HTTPError(code=422, msg=f"想定类型不存在：{obj.scenario_type_key}")
        if template.key not in scenario.environment_templates:
            raise errors.HTTPError(code=422, msg=f"想定类型 {scenario.name} 不支持环境模板 {template.name}")
        values = dict(obj.values)
        known = {field.key for field in template.fields}
        if set(values) - known:
            raise errors.HTTPError(code=422, msg="环境配置包含未知字段")
        for field in template.fields:
            value: Any = values.get(field.key, field.default)
            if field.required and value is None:
                raise errors.HTTPError(code=422, msg=f"{field.label}不能为空")
            if value is None:
                continue
            if field.type == "ipv4":
                chunks = str(value).split(".")
                if len(chunks) != 4 or not all(
                    chunk.isdigit() and 0 <= int(chunk) <= 255 for chunk in chunks
                ):
                    raise errors.HTTPError(code=422, msg=f"{field.label}必须是合法 IPv4 地址")
            elif field.type == "integer":
                if not isinstance(value, int) or not field.minimum <= value <= field.maximum:
                    raise errors.HTTPError(code=422, msg=f"{field.label}超出允许范围")
            elif value not in (field.options or []):
                raise errors.HTTPError(code=422, msg=f"{field.label}不在允许范围内")
            values[field.key] = value
        environment = EnvironmentConfig(
            template=obj.template,
            scenario_type_key=obj.scenario_type_key,
            values=values,
        )
        return environment, ValidationReport(
            status="valid",
            issues=[],
            summary={
                "环境模板": template.name,
                "想定类型": scenario.name,
                "默认连接阵营": f"{scenario.sides[0].name}（{scenario.sides[0].key}）",
                "连接地址": f"{values.get('ip', '—')}:{values.get('port', '—')}",
            },
        )

    def _build_detail(
        self,
        resource: Resource,
        versions: list[ResourceVersion],
        download_url: DownloadUrlBuilder,
    ) -> GetResourceDetail:
        summary = self._build_summary(resource, versions)
        return GetResourceDetail(
            **summary.model_dump(),
            versions=[self._build_version(version, download_url) for version in versions],
            created_at=resource.create_at,
        )

    def _build_summary(self, resource: Resource, versions: list[ResourceVersion]) -> GetResourceSummary:
        current = self._current_version(resource, versions)
        common = {
            "id": str(resource.id),
            "name": resource.name,
            "description": resource.description,
            "type": resource.type,
            "archived": resource.archived,
            "updated_at": resource.update_at or resource.create_at,
        }
        if resource.type == "environment":
            return GetResourceSummary(**common, environment=resource.environment)
        return GetResourceSummary(
            **common,
            current_version=current.version,
            current_version_id=str(current.id),
            format=current.format,
            version_count=len(versions),
        )

    @staticmethod
    def _current_version(resource: Resource, versions: list[ResourceVersion]) -> ResourceVersion:
        current = next((version for version in versions if version.id == resource.current_version_id), None)
        if not current:
            raise errors.ServerError(msg=f"资源 {resource.id} 缺少当前版本")
        return current

    @staticmethod
    def _build_version(version: ResourceVersion, download_url: DownloadUrlBuilder) -> ResourceVersionDetail:
        return ResourceVersionDetail(
            id=str(version.id),
            version=version.version,
            revision_number=version.revision_number,
            package_version=version.package_version,
            format=version.format,
            file_name=version.file_name,
            size=version.size,
            checksum=version.checksum,
            download_url=download_url(str(version.resource_id), str(version.id))
            if version.object_key
            else None,
            parsed_data=version.parsed_data,
            validation=version.validation,
            created_at=version.create_at,
        )

    async def _delete_object(self, object_key: str) -> None:
        try:
            await self.storage.delete(object_key)
        except Exception as exc:  # cleanup is deliberately best effort
            log.error("清理对象存储文件失败 {}: {}", object_key, exc)


resource_service = ResourceService(get_object_storage())
