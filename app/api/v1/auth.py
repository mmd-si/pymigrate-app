import asyncio
import requests
from urllib.parse import urljoin
from fastapi import APIRouter, Cookie, HTTPException, Response
from app.config.settings import get_settings
from app.dependencies import RequiresClientInfo, RequiresLocalDB
from app.schemas.external import ExternalAuth
from app.schemas.internal import ItemResponse
from app.schemas.request import LoginRequest
from app.schemas.response import SimpleSession
from app.services import auth


router = APIRouter(prefix='/auth')


@router.post('/login', response_model=ItemResponse[None])
async def login(db: RequiresLocalDB, data: LoginRequest, client: RequiresClientInfo, response: Response):
    settings = get_settings()
    unauthorized = HTTPException(
        401, detail='Por favor, revise sus credenciales e intente de nuevo.')
    url = urljoin(settings.mmdpawn_api_url, 'loginUsuario')
    try:
        res = await asyncio.to_thread(
            requests.get,
            url,
            params={
                'usuario': auth.mmdpawn_encrypt(data.username),
                'clave': auth.mmdpawn_encrypt(data.password),
            },
            timeout=10
        )
    except Exception as e:
        raise RuntimeError('Ocurrió un error desconocido al solicitar información del usuario en MMD Pawn') from e
        

    payload = ExternalAuth.model_validate(res.json())

    if not payload.can_continue():
        raise unauthorized

    if isinstance(payload.datos, str):
        raise unauthorized
    ttl = int(auth.session_ttl(data.remember_me).total_seconds())

    pysessid = await auth.create_session(
        db,
        payload,
        ip_address=client.ip_address,
        user_agent=client.user_agent,
        ttl=ttl
    )

    response.set_cookie(
        key='pysessid',
        value=pysessid,
        max_age=ttl,
        path='/',
        httponly=True,
        secure=True,
        samesite='none'
    )

    return ItemResponse(message='Autenticación exitosa', data=None)


@router.get('/session', response_model=ItemResponse[SimpleSession | None])
async def get_session_info(db: RequiresLocalDB, pysessid: str = Cookie(default=None)):
    not_authenticated = ItemResponse(message='No autenticado', data=None)
    if pysessid is None:
        return not_authenticated
    session = await auth.find_session(db, pysessid)
    if session is None:
        return not_authenticated
    return ItemResponse(message='Autenticado.', data=SimpleSession.from_session(session))


@router.post('/logout', response_model=ItemResponse[None])
async def logout(db: RequiresLocalDB, response: Response, pysessid: str = Cookie(default=None)):
    if pysessid is not None:
        await auth.revoke_session(db, pysessid)
    response.delete_cookie(key='pysessid', path='/', secure=True, samesite='none')
    return ItemResponse(message='Sesión cerrada', data=None)
