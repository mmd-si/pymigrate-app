from unittest.mock import AsyncMock, patch

from app.api.v1 import branch as branch_router
from app.dependencies import require_session
from app.main import app
from tests.support.builders import make_branch_row, make_session


async def test_index_branch_master_lists_all_branches_with_clamped_pagination(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=999)
    rows = [make_branch_row(id=1, name='Uno'), make_branch_row(id=2, name='Dos')]

    with patch.object(branch_router.branch, 'all', new=AsyncMock(return_value=[
        branch_router.SimpleBranch.from_row(r) for r in rows
    ])) as branch_all:
        response = await app_client.get('/api/v1/branches/', params={'limit': 500, 'offset': -5})

    assert response.status_code == 200
    body = response.json()
    assert [b['id'] for b in body['data']] == [1, 2]
    branch_all.assert_awaited_once()
    call_args = branch_all.call_args.args
    assert call_args[1] == 100  # limit clamped to 100
    assert call_args[2] == 0    # offset clamped to 0


async def test_index_non_master_sees_only_their_own_branch(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=826)
    own_branch = branch_router.SimpleBranch.from_row(make_branch_row(id=826, name='Sucursal Propia'))

    with patch.object(branch_router.branch, 'by_id', new=AsyncMock(return_value=own_branch)) as by_id, \
         patch.object(branch_router.branch, 'all', new=AsyncMock()) as branch_all:
        response = await app_client.get('/api/v1/branches/')

    assert response.status_code == 200
    body = response.json()
    assert [b['id'] for b in body['data']] == [826]
    by_id.assert_awaited_once()
    assert by_id.call_args.args[1] == 826
    branch_all.assert_not_called()


async def test_index_non_master_branch_not_found_returns_404(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=826)

    with patch.object(branch_router.branch, 'by_id', new=AsyncMock(return_value=None)):
        response = await app_client.get('/api/v1/branches/')

    assert response.status_code == 404


async def test_show_returns_branch_when_found(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=999)
    found = branch_router.SimpleBranch.from_row(make_branch_row(id=5, name='Cinco'))

    with patch.object(branch_router.branch, 'by_id', new=AsyncMock(return_value=found)):
        response = await app_client.get('/api/v1/branches/5')

    assert response.status_code == 200
    assert response.json()['data']['id'] == 5


async def test_show_returns_404_when_not_found(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=999)

    with patch.object(branch_router.branch, 'by_id', new=AsyncMock(return_value=None)):
        response = await app_client.get('/api/v1/branches/404')

    assert response.status_code == 404


async def test_show_returns_403_for_non_master_requesting_a_different_branch(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=826)

    with patch.object(branch_router.branch, 'by_id', new=AsyncMock()) as by_id:
        response = await app_client.get('/api/v1/branches/999')

    assert response.status_code == 403
    by_id.assert_not_called()


async def test_show_allows_non_master_requesting_their_own_branch(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=826)
    own_branch = branch_router.SimpleBranch.from_row(make_branch_row(id=826, name='Sucursal Propia'))

    with patch.object(branch_router.branch, 'by_id', new=AsyncMock(return_value=own_branch)):
        response = await app_client.get('/api/v1/branches/826')

    assert response.status_code == 200
