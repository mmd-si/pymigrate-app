from unittest.mock import AsyncMock, patch

from app.models.local import TransferJobItem
from app.schemas.response import InventoryDetails
from app.services import transfer
from tests.support.builders import make_inventory_row, make_job_item, make_transfer_job, mock_db, mock_result


async def test_create_returns_none_and_skips_writes_when_no_valid_barcodes():
    lcl = mock_db()
    rmt = mock_db()

    with patch.object(transfer.inventory, 'existing_only', new=AsyncMock(return_value=[])):
        result = await transfer.create(lcl, rmt, ['BC001'], owner_id='user-1')

    assert result is None
    lcl.add.assert_not_called()
    lcl.flush.assert_not_awaited()


async def test_create_builds_job_and_one_item_per_valid_barcode():
    lcl = mock_db()
    rmt = mock_db()

    with patch.object(transfer.inventory, 'existing_only', new=AsyncMock(return_value=['BC001', 'BC002'])):
        job_id = await transfer.create(lcl, rmt, ['BC001', 'BC002', 'BC003'], owner_id='user-1')

    lcl.add.assert_called_once()
    job = lcl.add.call_args.args[0]
    assert job.owner_id == 'user-1'
    assert job.job_id == job_id
    assert len(job.items) == 2
    assert {item.row_id for item in job.items} == {'BC001', 'BC002'}
    assert all(isinstance(item, TransferJobItem) for item in job.items)
    lcl.flush.assert_awaited_once()


async def test_list_summary_returns_empty_without_summarizing_when_no_jobs():
    db = mock_db()
    db.execute.return_value = mock_result(scalars=mock_result(all=[]))

    result = await transfer.list_summary(db, owner_id='user-1', limit=20, offset=0)

    assert result == []


async def test_list_summary_returns_one_summary_per_job():
    db = mock_db()
    jobs = [make_transfer_job(owner_id='user-1'), make_transfer_job(owner_id='user-1')]
    db.execute.return_value = mock_result(scalars=mock_result(all=jobs))

    result = await transfer.list_summary(db, owner_id='user-1', limit=20, offset=0)

    assert len(result) == 2
    assert {s.job_id for s in result} == {j.job_id for j in jobs}


async def test_detailed_returns_none_without_fetching_inventory_when_job_not_found():
    lcl = mock_db()
    rmt = mock_db()
    lcl.execute.return_value = mock_result(scalar_one_or_none=None)

    with patch.object(transfer.inventory, 'group_by_barcodes', new=AsyncMock()) as group_by_barcodes:
        result = await transfer.detailed(lcl, rmt, job_id='missing', owner_id='user-1')

    assert result is None
    group_by_barcodes.assert_not_called()


async def test_detailed_composes_job_with_remote_inventory():
    lcl = mock_db()
    rmt = mock_db()
    item = make_job_item(row_id='BC001')
    job = make_transfer_job(items=[item], errors=[])
    lcl.execute.return_value = mock_result(scalar_one_or_none=job)
    products = {'BC001': InventoryDetails.from_row(make_inventory_row(barcode='BC001'))}

    with patch.object(transfer.inventory, 'group_by_barcodes', new=AsyncMock(return_value=products)) as group_by_barcodes:
        result = await transfer.detailed(lcl, rmt, job_id=job.job_id, owner_id='user-1')

    group_by_barcodes.assert_awaited_once_with(rmt, ['BC001'])
    assert result is not None
    assert result.job_id == job.job_id
    assert len(result.items) == 1
