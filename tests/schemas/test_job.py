from datetime import timedelta

from app.schemas.response import DetailedJob, ErrorSummary, JobSummary
from app.core.utils import utcnow
from tests.support.builders import make_job_error, make_job_item, make_transfer_job


def test_job_summary_latest_error_is_none_when_no_errors():
    job = make_transfer_job(errors=[])
    summary = JobSummary.from_populated(job)
    assert summary.latest_error is None


def test_job_summary_latest_error_picks_max_occurred_at_not_first_or_last():
    now = utcnow()
    oldest = make_job_error(message='oldest', occurred_at=now - timedelta(hours=2))
    newest = make_job_error(message='newest', occurred_at=now)
    middle = make_job_error(message='middle', occurred_at=now - timedelta(hours=1))
    # Inserted out of chronological order on purpose: neither first nor last
    # in this list is the newest, so a naive "first"/"last" pick would fail.
    job = make_transfer_job(errors=[middle, oldest, newest])

    summary = JobSummary.from_populated(job)

    assert summary.latest_error == ErrorSummary.from_model(newest)


def test_detailed_job_drops_items_with_no_matching_inventory():
    item_in_stock = make_job_item(row_id='BC001')
    item_missing = make_job_item(row_id='BC002')
    job = make_transfer_job(items=[item_in_stock, item_missing], errors=[])

    from app.schemas.response import InventoryDetails
    from tests.support.builders import make_inventory_row
    inventory = {'BC001': InventoryDetails.from_row(make_inventory_row(barcode='BC001'))}

    detailed = DetailedJob.from_populated(job, inventory)

    assert len(detailed.items) == 1
    assert detailed.items[0].item_id == item_in_stock.item_id


def test_detailed_job_includes_all_errors_unconditionally():
    job = make_transfer_job(items=[], errors=[make_job_error(), make_job_error()])
    detailed = DetailedJob.from_populated(job, inventory={})
    assert len(detailed.errors) == 2
