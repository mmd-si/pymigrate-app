from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import v1
from app.dependencies import RequiresLocalDB, RequiresRemoteDB
from app.schemas.internal import AppMessage

router = APIRouter(prefix='/api')

@router.get('/health')
async def health(response: Response, lcl: RequiresLocalDB, rmt: RequiresRemoteDB):
    select_1 = text('SELECT 1')
    local_ok = True
    remote_ok = True

    try:
        await lcl.execute(select_1)
    except SQLAlchemyError:
        local_ok = False

    try:
        await rmt.execute(select_1)
    except SQLAlchemyError:
        remote_ok = False

    if not local_ok:
        message = AppMessage.warning('Base de datos local inaccesible')
    elif not remote_ok:
        message = AppMessage.warning('Base de datos remota inaccesible')
    else:
        message = AppMessage.success('Todos los sistemas operativos')

    response.status_code = 200 if local_ok and remote_ok else 503

    return { 'status': response.status_code, **message.dict() }

router.include_router(v1.router)
