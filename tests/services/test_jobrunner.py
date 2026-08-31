from app.models.local import ItemResult, JobResult, JobStatus
from app.services import jobrunner
from tests.support.builders import (
    make_job_item,
    make_transfer_job,
    mock_db,
    mock_result,
)


async def test_claim_pending_marks_jobs_processing_and_bumps_tries():
    lcl = mock_db()
    jobs = [make_transfer_job(tries=0), make_transfer_job(tries=2)]
    lcl.scalars.return_value = mock_result(all=jobs)

    claimed = await jobrunner.claim_pending(lcl, limit=10, max_tries=3)

    assert claimed == jobs
    for job in jobs:
        assert job.status is JobStatus.Processing
        assert job.shifted_at is not None
    assert [j.tries for j in jobs] == [1, 3]
    lcl.commit.assert_not_awaited()  # caller commits


def test_outstanding_items_excludes_successful():
    job = make_transfer_job(
        items=[
            make_job_item(row_id='A', result=ItemResult.Pending),
            make_job_item(row_id='B', result=ItemResult.Success),
            make_job_item(row_id='C', result=ItemResult.Failure),
        ]
    )
    assert {i.row_id for i in jobrunner.outstanding_items(job)} == {'A', 'C'}


async def test_finish_job_sets_completed_and_result():
    lcl = mock_db()
    job = make_transfer_job()

    await jobrunner.finish_job(lcl, job, JobResult.Success)

    assert job.status is JobStatus.Completed
    assert job.result is JobResult.Success
    assert job.completed_at is not None
    lcl.flush.assert_awaited()


async def test_mark_item_sets_result():
    lcl = mock_db()
    item = make_job_item(result=ItemResult.Pending)

    await jobrunner.mark_item(lcl, item, ItemResult.Failure)

    assert item.result is ItemResult.Failure


async def test_record_error_adds_row():
    lcl = mock_db()

    await jobrunner.record_error(
        lcl, 'job-1', 'boom', description='while mapping', item_id='item-1'
    )

    lcl.add.assert_called_once()
    error = lcl.add.call_args.args[0]
    assert error.job_id == 'job-1'
    assert error.message == 'boom'
    assert error.description == 'while mapping'
    assert error.item_id == 'item-1'
    assert error.occurred_at is not None
