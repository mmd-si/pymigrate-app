from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.local import JobStatus, TransferJob, TransferJobItem
from app.services import inventory
from app.schemas.response import DetailedJob, JobSummary

async def create(
    lcl: AsyncSession, 
    rmt: AsyncSession, 
    barcodes: list[str], 
    owner_id: str
) -> str | None:
    barcodes = await inventory.existing_only(rmt, barcodes)
    if not barcodes:
        return None
    job = TransferJob(owner_id=owner_id)
    job.items = [TransferJobItem(job=job, row_id=bc) for bc in barcodes]
    lcl.add(job)
    await lcl.flush()
    return job.job_id


async def get(lcl: AsyncSession, job_id: str, owner_id: str) -> TransferJob | None:
    stmt = select(TransferJob).where(
        TransferJob.job_id == job_id, TransferJob.owner_id == owner_id
    )
    result = await lcl.execute(stmt)
    return result.scalar_one_or_none()


async def list_summary(db: AsyncSession, owner_id: str, limit: int, offset: int, status: JobStatus | None = None) -> list[JobSummary]:
    where = [TransferJob.owner_id == owner_id]

    if status is not None:
        where.append(TransferJob.status == status)

    stmt = (
        select(TransferJob)
            .where(*where)
            .order_by(TransferJob.pushed_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(TransferJob.items), selectinload(TransferJob.errors))
    )
    result = await db.execute(stmt)
    jobs = list(result.scalars().all())
    if not jobs:
        return []
    return [JobSummary.from_populated(j) for j in jobs]


async def detailed(lcl: AsyncSession, rmt: AsyncSession, job_id: str, owner_id: str) -> DetailedJob | None:
    stmt = (
        select(TransferJob)
        .where(TransferJob.job_id == job_id, TransferJob.owner_id == owner_id)
        .options(selectinload(TransferJob.items), selectinload(TransferJob.errors))
    )
    result = await lcl.execute(stmt)
    job = result.scalar_one_or_none()

    if job is None:
        return None

    products = await inventory.group_by_barcodes(rmt, [item.row_id for item in job.items])
    return DetailedJob.from_populated(job, products)