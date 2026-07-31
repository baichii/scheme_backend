# Scheme Backend Agent Guide

## Architecture Baseline

- Use [fastapi-practices/fastapi-best-architecture](https://github.com/fastapi-practices/fastapi-best-architecture) as the baseline for Python module organization, class names, function names, and layer responsibilities.
- This repository is a deliberately reduced adaptation. Do not add upstream features such as RBAC, plugins, soft deletion, response acceleration, or middleware unless the task requires them.
- Preserve the existing domain layout: `backend/app/<domain>/{api,crud,model,schema,service}`.

## Contract Priority

- Frontend-facing data models and REST payloads follow `scheme_frontend` contracts.
- Engine-facing requests and runtime states follow the Matrix protocol.
- Cross-component domain naming follows `scheme_integrate/docs/terminology.md`; update that document when a shared term or mapping changes.
- Architecture conventions must not change wire contracts. In particular, V2 APIs may return direct JSON when required by the frontend instead of the legacy `{code,msg,data}` envelope.

## Naming Conventions

- CRUD classes: `CRUD<Entity>`; singleton instances: `<entity>_dao`.
- Services: `<Entity>Service`; singleton instances: `<entity>_service`; public methods are `@staticmethod` unless instance state is required.
- Request schemas: `Create<Entity>Param`, `Update<Entity>Param`, `Delete<Entity>Param`.
- Internal persistence schemas: `Create<Entity>Internal` or `Update<Entity>Internal`.
- Response schemas: `Get<Entity>Detail`, `Get<Entity>Summary`, `Get<Entity>Page`.
- API functions: `get_<entity>_list`, `get_<entity>_by_id`, `create_<entity>`, `update_<entity>`, `delete_<entity>`.
- CRUD and service primary-key parameters use `pk`; API path parameters may use domain-specific names required by the public contract.
- Prefer established project terms such as `obj`, `param`, `pk`, `count`, and `<entity>_dao`; avoid introducing `Request`, `Payload`, `Repository`, or `Manager` naming without a protocol-level reason.

## Layer Responsibilities

- API modules handle HTTP parsing, response models, and status codes.
- Schema modules contain Pydantic validation and wire aliases.
- Service modules contain business validation and orchestration and raise errors from `backend.common.exception.errors`.
- CRUD modules inherit `CRUDPlus` and contain database queries only.
- Model modules contain SQLAlchemy persistence definitions only.
- Reuse `SchemaBase`, `CurrentSession`, `CurrentSessionTransaction`, common responses, and common exceptions before introducing new infrastructure.

## Change Discipline

- Match the surrounding domain style before creating new modules or abstractions.
- Do not add compatibility layers for obsolete V1 contracts unless explicitly requested.
- Keep Engine protocol schemas separate from SQLAlchemy models.
- Add async tests with temporary or isolated databases for new data APIs; external services must not be required for unit tests.
- Run focused pytest, Ruff check, Ruff format check, and `git diff --check` before completion.
