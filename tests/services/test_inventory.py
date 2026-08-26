from unittest.mock import AsyncMock

from app.services import inventory
from tests.support.builders import make_inventory_row, mock_result


async def test_by_branch_and_barcode_returns_details_when_found():
    db = AsyncMock()
    db.execute.return_value = mock_result(first=make_inventory_row(barcode='BC001'))

    result = await inventory.by_branch_and_barcode(db, branch_id=1, barcode='BC001')

    assert result is not None
    assert result.barcode == 'BC001'


async def test_by_branch_and_barcode_returns_none_when_not_found():
    db = AsyncMock()
    db.execute.return_value = mock_result(first=None)

    result = await inventory.by_branch_and_barcode(db, branch_id=1, barcode='NOPE')

    assert result is None


async def test_with_barcode_in_returns_empty_without_querying_when_no_barcodes():
    db = AsyncMock()

    result = await inventory.with_barcode_in(db, [])

    assert result == []
    db.execute.assert_not_called()


async def test_with_barcode_in_maps_all_rows():
    db = AsyncMock()
    db.execute.return_value = [make_inventory_row(barcode='BC001'), make_inventory_row(barcode='BC002')]

    result = await inventory.with_barcode_in(db, ['BC001', 'BC002'])

    assert [r.barcode for r in result] == ['BC001', 'BC002']


async def test_group_by_barcodes_returns_empty_without_querying_when_no_barcodes():
    db = AsyncMock()

    result = await inventory.group_by_barcodes(db, [])

    assert result == {}
    db.execute.assert_not_called()


async def test_group_by_barcodes_keys_by_barcode():
    db = AsyncMock()
    db.execute.return_value = [make_inventory_row(barcode='BC001'), make_inventory_row(barcode='BC002')]

    result = await inventory.group_by_barcodes(db, ['BC001', 'BC002'])

    assert set(result.keys()) == {'BC001', 'BC002'}
    assert result['BC001'].barcode == 'BC001'


async def test_existing_only_returns_just_barcodes():
    db = AsyncMock()
    db.execute.return_value = [make_inventory_row(barcode='BC001'), make_inventory_row(barcode='BC002')]

    result = await inventory.existing_only(db, ['BC001', 'BC002', 'BC003'])

    assert result == ['BC001', 'BC002']
