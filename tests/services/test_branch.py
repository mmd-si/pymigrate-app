from unittest.mock import AsyncMock

from app.services import branch
from tests.support.builders import make_branch_row, mock_result


async def test_all_maps_rows_to_simple_branch():
    db = AsyncMock()
    db.execute.return_value = mock_result(all=[
        make_branch_row(id=1, name='Uno'),
        make_branch_row(id=2, name='Dos'),
    ])

    result = await branch.all(db, limit=20, offset=0)

    assert [b.id for b in result] == [1, 2]
    assert [b.name for b in result] == ['Uno', 'Dos']


async def test_all_returns_empty_list_when_no_rows():
    db = AsyncMock()
    db.execute.return_value = mock_result(all=[])

    result = await branch.all(db, limit=20, offset=0)

    assert result == []


async def test_by_id_returns_simple_branch_when_found():
    db = AsyncMock()
    db.execute.return_value = mock_result(one_or_none=make_branch_row(id=5, name='Cinco'))

    result = await branch.by_id(db, 5)

    assert result.id == 5
    assert result.name == 'Cinco'


async def test_by_id_returns_none_when_not_found():
    db = AsyncMock()
    db.execute.return_value = mock_result(one_or_none=None)

    result = await branch.by_id(db, 999)

    assert result is None
