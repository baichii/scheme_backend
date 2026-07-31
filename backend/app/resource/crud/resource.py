from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.resource.model.resource import (
    Resource,
    ResourceVersion,
    agent_resource_id_sequence,
)


class CRUDResource(CRUDPlus[Resource]):
    async def get(self, db: AsyncSession, pk: int) -> Resource | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, *, resource_type: str, name: str) -> Resource | None:
        result = await db.execute(
            select(Resource).where(
                Resource.type == resource_type,
                Resource.normalized_name == name.casefold(),
            )
        )
        return result.scalar_one_or_none()

    async def get_list(self, db: AsyncSession) -> list[Resource]:
        result = await db.execute(select(Resource))
        return list(result.scalars())

    async def next_agent_id(self, db: AsyncSession) -> int:
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            value = await db.scalar(select(agent_resource_id_sequence.next_value()))
            return int(value)
        value = await db.scalar(select(func.max(Resource.id)).where(Resource.type == "agent"))
        return max(int(value or 9999) + 1, 10000)

    async def create(self, db: AsyncSession, values: dict) -> Resource:
        resource = Resource(**values)
        db.add(resource)
        await db.flush()
        return resource

    async def update(self, db: AsyncSession, pk: int, values: dict) -> int:
        return await self.update_model(db, pk, values, flush=True)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model(db, pk, flush=True)


class CRUDResourceVersion(CRUDPlus[ResourceVersion]):
    async def get(self, db: AsyncSession, pk: int) -> ResourceVersion | None:
        return await self.select_model(db, pk)

    async def get_list(self, db: AsyncSession, resource_id: int) -> list[ResourceVersion]:
        result = await db.execute(
            select(ResourceVersion)
            .where(ResourceVersion.resource_id == resource_id)
            .order_by(ResourceVersion.revision_number.desc().nullslast(), ResourceVersion.create_at.desc())
        )
        return list(result.scalars())

    async def get_by_version(
        self, db: AsyncSession, resource_id: int, version: str
    ) -> ResourceVersion | None:
        result = await db.execute(
            select(ResourceVersion).where(
                ResourceVersion.resource_id == resource_id,
                ResourceVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_checksum(
        self, db: AsyncSession, resource_id: int, checksum: str
    ) -> ResourceVersion | None:
        result = await db.execute(
            select(ResourceVersion).where(
                ResourceVersion.resource_id == resource_id,
                ResourceVersion.checksum == checksum,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, values: dict) -> ResourceVersion:
        version = ResourceVersion(**values)
        db.add(version)
        await db.flush()
        return version


resource_dao: CRUDResource = CRUDResource(Resource)
resource_version_dao: CRUDResourceVersion = CRUDResourceVersion(ResourceVersion)
