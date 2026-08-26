from fastapi import APIRouter, HTTPException
from app.dependencies import RequiresRemoteDB, RequiresSession
from app.schemas.internal import ItemResponse
from app.services import inventory

router = APIRouter(prefix='/inventory')

@router.get('/{barcode}')
async def show(db: RequiresRemoteDB, current: RequiresSession, branch_id: int, barcode: str):
    if not current.is_branch_master() and not current.branch_id == branch_id:
        raise HTTPException(403, 'Lo sentimos. No está autorizado/a para acceder a esta información.')

    product = await inventory.by_branch_and_barcode(db, branch_id, barcode)
    if product is None:
        raise HTTPException(404, detail='No se encontró un producto con este código de barra')

    return ItemResponse(
        message='Se encontró el producto en el inventario.',
        data=product
    )