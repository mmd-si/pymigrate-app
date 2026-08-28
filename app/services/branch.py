from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.remote import Branch
from app.schemas.response import SimpleBranch

GRUPO_SI = 3

async def all(db: AsyncSession, limit: int, offset: int) -> list[SimpleBranch]:
    stmt = select(
        Branch.id.label('id'),
        Branch.nombreComercial.label('name'),
        Branch.siglas.label('acronym')
    ).where(Branch.grupo == GRUPO_SI).limit(limit).offset(offset).order_by(Branch.id)

    result = await db.execute(stmt)

    return [SimpleBranch.from_row(row) for row in result.all()]

async def by_id(db: AsyncSession, branch_id: int) -> SimpleBranch | None:
    stmt = select(
        Branch.id.label('id'),
        Branch.nombreComercial.label('name'),
        Branch.siglas.label('acronym')
    ).where(Branch.grupo == GRUPO_SI, Branch.id == branch_id)

    result = await db.execute(stmt)
    if (row := result.one_or_none()) is None:
        return None
    return SimpleBranch.from_row(row)