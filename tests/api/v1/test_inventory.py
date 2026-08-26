from unittest.mock import AsyncMock, patch

from app.api.v1 import inventory as inventory_router
from app.dependencies import require_session
from app.main import app
from app.schemas.response import InventoryDetails
from tests.support.builders import make_inventory_row, make_session


async def test_show_returns_product_when_found(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=999)
    product = InventoryDetails.from_row(make_inventory_row(barcode='BC001'))

    with patch.object(inventory_router.inventory, 'by_branch_and_barcode', new=AsyncMock(return_value=product)):
        response = await app_client.get('/api/v1/branches/1/inventory/BC001')

    assert response.status_code == 200
    assert response.json()['data']['barcode'] == 'BC001'


async def test_show_returns_404_when_barcode_not_found(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=999)

    with patch.object(inventory_router.inventory, 'by_branch_and_barcode', new=AsyncMock(return_value=None)):
        response = await app_client.get('/api/v1/branches/1/inventory/NOPE')

    assert response.status_code == 404


async def test_show_returns_403_for_non_master_requesting_a_different_branch(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=826)

    with patch.object(inventory_router.inventory, 'by_branch_and_barcode', new=AsyncMock()) as lookup:
        response = await app_client.get('/api/v1/branches/999/inventory/BC001')

    assert response.status_code == 403
    lookup.assert_not_called()


async def test_show_allows_non_master_requesting_their_own_branch(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=826)
    product = InventoryDetails.from_row(make_inventory_row(barcode='BC001'))

    with patch.object(inventory_router.inventory, 'by_branch_and_barcode', new=AsyncMock(return_value=product)):
        response = await app_client.get('/api/v1/branches/826/inventory/BC001')

    assert response.status_code == 200


async def test_show_unexpected_exception_surfaces_as_generic_500(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(branch_id=999)

    with patch.object(inventory_router.inventory, 'by_branch_and_barcode', new=AsyncMock(side_effect=RuntimeError('boom'))):
        response = await app_client.get('/api/v1/branches/1/inventory/BC001')

    assert response.status_code == 500
    assert response.json() == {'detail': 'Hubo un error inesperado.'}
