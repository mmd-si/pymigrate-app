from fastapi import APIRouter, HTTPException
from app.api.v1 import inventory
from app.core.utils import clamp
from app.dependencies import RequiresRemoteDB, RequiresSession
from app.schemas.internal import ListResponse, ItemResponse
from app.schemas.response import SimpleBranch
from app.services import branch

router = APIRouter(prefix='/branches')


@router.get('/', response_model=ListResponse[SimpleBranch])
async def index(db: RequiresRemoteDB, current: RequiresSession, limit: int = 20, offset: int = 0):
    branches = []
    if current.is_branch_master():
        limit = clamp(limit, 0, 100)
        offset = max(0, offset)
        branches = await branch.all(db, limit, offset)
    else:
        br = await branch.by_id(db, current.branch_id)
        if br is None:
            raise HTTPException(404, 'No se pudo encontrar la sucursal solicitada.')
        branches.append(br)

    return ListResponse(message='Se encontraron las sucursales exitosamente.', data=branches)

@router.get('/{branch_id}', response_model=ItemResponse[SimpleBranch])
async def show(db: RequiresRemoteDB, current: RequiresSession, branch_id: int):
    if not current.is_branch_master() and not current.branch_id == branch_id:
        raise HTTPException(403, 'Lo sentimos. No está autorizado/a para acceder a esta información.')

    br = await branch.by_id(db, branch_id)

    if br is None:
        raise HTTPException(404, 'No se pudo encontrar la sucursal solicitada.')

    return ItemResponse(message="Se encontró la sucursal exitosamente", data=br)


router.include_router(inventory.router, prefix='/{branch_id}')