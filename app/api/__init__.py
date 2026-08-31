import asyncio
import logging

from fastapi import APIRouter, Request, Response
import requests
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import v1
from app.config.settings import get_settings
from app.dependencies import RequiresLocalDB, RequiresRemoteDB
from app.schemas.internal import AppMessage, ItemResponse
from app.services import flash

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api')

settings = get_settings()

@router.get('/health')
async def health(response: Response, lcl: RequiresLocalDB, rmt: RequiresRemoteDB):
    select_1 = text('SELECT 1')
    local_ok = True
    remote_ok = True
    mmdpawn_ok = True

    try:
        await lcl.execute(select_1)
    except SQLAlchemyError:
        local_ok = False

    try:
        await rmt.execute(select_1)
    except SQLAlchemyError:
        remote_ok = False

    try:
        res = await asyncio.to_thread(
            requests.get,
            settings.mmdpawn_api_url,
            timeout=5
        )
        res.raise_for_status()
    except Exception:
        mmdpawn_ok = False

    if not local_ok:
        msg = AppMessage.warning('Base de datos local inaccesible')
    elif not remote_ok:
        msg = AppMessage.warning('Base de datos remota inaccesible')
    elif not mmdpawn_ok:
        msg = AppMessage.warning('API de MMD Pawn inaccesible')
    else:
        msg = AppMessage.success('Todos los sistemas operativos')

    response.status_code = 200 if local_ok and remote_ok else 503

    logger.info(msg.message)

    return { 'status': response.status_code, **msg.dict() }

@router.get('/flash', response_model=ItemResponse[AppMessage | None])
async def get_flash(request: Request, response: Response):
    data = flash.read(request, response)
    return ItemResponse(message='', data=AppMessage(**data) if data else None)

router.include_router(v1.router)
