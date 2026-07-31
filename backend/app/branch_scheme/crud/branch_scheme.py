from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.branch_scheme.model.branch_scheme import BranchScheme, BranchSchemeRevision


class CRUDBranchScheme(CRUDPlus[BranchScheme]):
    async def get(self, db: AsyncSession, pk: int) -> BranchScheme | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> BranchScheme | None:
        result = await db.execute(
            select(BranchScheme).where(BranchScheme.normalized_name == name.casefold())
        )
        return result.scalar_one_or_none()

    async def get_list(self, db: AsyncSession) -> list[BranchScheme]:
        result = await db.execute(select(BranchScheme))
        return list(result.scalars())

    async def create(self, db: AsyncSession, values: dict) -> BranchScheme:
        scheme = BranchScheme(**values)
        db.add(scheme)
        await db.flush()
        return scheme

    async def compare_and_swap_head(
        self,
        db: AsyncSession,
        *,
        pk: int,
        base_revision_id: int,
        values: dict,
    ) -> bool:
        result = await db.execute(
            update(BranchScheme)
            .where(BranchScheme.id == pk, BranchScheme.head_revision_id == base_revision_id)
            .values(**values)
        )
        await db.flush()
        return result.rowcount == 1

    async def delete(self, db: AsyncSession, pk: int) -> None:
        await db.execute(delete(BranchSchemeRevision).where(BranchSchemeRevision.branch_scheme_id == pk))
        await db.execute(delete(BranchScheme).where(BranchScheme.id == pk))
        await db.flush()


class CRUDBranchSchemeRevision(CRUDPlus[BranchSchemeRevision]):
    async def get(self, db: AsyncSession, pk: int) -> BranchSchemeRevision | None:
        return await self.select_model(db, pk)

    async def get_list(self, db: AsyncSession, branch_scheme_id: int) -> list[BranchSchemeRevision]:
        result = await db.execute(
            select(BranchSchemeRevision)
            .where(BranchSchemeRevision.branch_scheme_id == branch_scheme_id)
            .order_by(BranchSchemeRevision.revision_number.desc())
        )
        return list(result.scalars())

    async def get_all(self, db: AsyncSession) -> list[BranchSchemeRevision]:
        result = await db.execute(select(BranchSchemeRevision))
        return list(result.scalars())

    async def create(self, db: AsyncSession, values: dict) -> BranchSchemeRevision:
        revision = BranchSchemeRevision(**values)
        db.add(revision)
        await db.flush()
        return revision


branch_scheme_dao: CRUDBranchScheme = CRUDBranchScheme(BranchScheme)
branch_scheme_revision_dao: CRUDBranchSchemeRevision = CRUDBranchSchemeRevision(BranchSchemeRevision)
