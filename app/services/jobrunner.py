"""Consumer-side persistence for transfer jobs: claiming pending work and
recording per-job / per-item outcomes and errors.

Ported from ``pymigrate/migrate-worker/app/repository/transfer_job*_repository.py``
(sync ``Session`` -> ``AsyncSession``). The HTTP-facing reads stay in
``app.services.transfer``.
"""

from sqlalchemy import and_, nulls_first, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import utcnow
from app.models.local import (
    ItemResult,
    JobResult,
    JobStatus,
    TransferJob,
    TransferJobError,
    TransferJobItem,
)


async def claim_pending(lcl: AsyncSession, limit: int, max_tries: int) -> list[TransferJob]:
    """Lock and claim up to ``limit`` jobs that are pending or failed-with-retries
    left, flipping them to ``Processing``. Uses ``FOR UPDATE SKIP LOCKED`` so
    concurrent drains (multiple replicas / a scheduler tick racing a POST kick)
    never claim the same rows.
    """
    stmt = (
        select(TransferJob)
        .where(
            or_(
                TransferJob.status == JobStatus.Pending,
                and_(
                    TransferJob.result == JobResult.Failure,
                    TransferJob.tries < max_tries,
                ),
            )
        )
        .order_by(nulls_first(TransferJob.result), TransferJob.pushed_at)
        .with_for_update(skip_locked=True)
        .limit(limit)
        .options(selectinload(TransferJob.items))
    )
    jobs = list((await lcl.scalars(stmt)).all())

    now = utcnow()
    for job in jobs:
        job.status = JobStatus.Processing
        job.shifted_at = now
        job.tries += 1

    return jobs


def outstanding_items(job: TransferJob) -> list[TransferJobItem]:
    """Items still needing work (Pending or Failure). Requires ``items`` to be
    eagerly loaded (``claim_pending`` does this)."""
    return [i for i in job.items if i.result != ItemResult.Success]


async def mark_item(lcl: AsyncSession, item: TransferJobItem, result: ItemResult) -> None:
    item.result = result
    await lcl.flush()


async def finish_job(lcl: AsyncSession, job: TransferJob, result: JobResult) -> None:
    job.status = JobStatus.Completed
    job.completed_at = utcnow()
    job.result = result
    await lcl.flush()


async def record_error(
    lcl: AsyncSession,
    job_id: str,
    message: str,
    *,
    description: str | None = None,
    item_id: str | None = None,
) -> None:
    lcl.add(
        TransferJobError(
            job_id=job_id,
            message=message,
            description=description,
            item_id=item_id,
            occurred_at=utcnow(),
        )
    )
    await lcl.flush()
