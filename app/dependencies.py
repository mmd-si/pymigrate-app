from typing import Annotated, AsyncIterator
from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.db import LocalSession, RemoteSession
from app.config.settings import get_settings
from app.models.local import Session
from app.schemas.internal import ClientInfo
from app.services import auth


async def get_local_db() -> AsyncIterator[AsyncSession]:
    async with LocalSession() as session:
        yield session

RequiresLocalDB = Annotated[AsyncSession, Depends(get_local_db)]

async def get_remote_db() -> AsyncIterator[AsyncSession]:
    async with RemoteSession() as session:
        yield session

RequiresRemoteDB = Annotated[AsyncSession, Depends(get_remote_db)]

def get_client_info(request: Request) -> ClientInfo:
    settings = get_settings()

    if settings.trust_proxy:
        forwarded_for = request.headers.get('x-forwarded-for')
        ip_address = forwarded_for.split(',')[0].strip() if forwarded_for else None
    else:
        ip_address = request.client.host if request.client else None

    user_agent = request.headers.get('user-agent')

    return ClientInfo(ip_address=ip_address, user_agent=user_agent)

RequiresClientInfo = Annotated[ClientInfo, Depends(get_client_info)]

async def require_session(db: RequiresLocalDB, pysessid: str = Cookie(default=None)) -> Session:
    unauthorized = HTTPException(401, detail='Por favor iniciar sesión antes de continuar.')
    if pysessid is None:
        raise unauthorized
    session = await auth.find_session(db, pysessid)
    if session is None:
        raise unauthorized
    return session

RequiresSession = Annotated[Session, Depends(require_session)]