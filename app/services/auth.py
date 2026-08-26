import hashlib
import secrets
import urllib.parse
from datetime import timedelta
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import get_settings
from app.core.utils import utcnow
from app.models.local import Session
from app.schemas.external import ExternalAuth
from app.services import crypto


settings = get_settings()

_MMDPAWN_IV = b"\x00" * 16
_MMDPAWN_KEY = hashlib.sha256(settings.mmdpawn_encrypt_pw.encode()).digest()[:32]

def session_ttl(remember_me: bool) -> timedelta:
    return timedelta(days=30) if remember_me else timedelta(days=7)

async def create_session(
    db: AsyncSession, 
    data: ExternalAuth, 
    ip_address: str, 
    user_agent: str, 
    ttl: int
):
    now = utcnow()
    pysessid = secrets.token_urlsafe(48)
    session = Session(
        pysessid=crypto.sha256hash(pysessid),
        user_id=str(data.datos.login.idLogin),
        branch_id=int(data.datos.info.idSucursal),
        role_id=int(data.datos.info.idPerfil),
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl),
        data = {
            'firstName': data.datos.info.nombre,
            'lastName': data.datos.info.apellido
        }  
    )
    db.add(session)
    await db.flush()
    return pysessid

async def revoke_session(db: AsyncSession, pysessid: str) -> None:
    stmt = delete(Session).where(Session.pysessid == crypto.sha256hash(pysessid))
    await db.execute(stmt)
    await db.flush()

async def find_session(db: AsyncSession, pysessid: str) -> Session | None:
    stmt = select(Session).where(Session.pysessid == crypto.sha256hash(pysessid))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        return None
    if session.expires_at <= utcnow():
        await revoke_session(db, pysessid)
        return None
    return session

def mmdpawn_encrypt(text: str) -> str:
    return crypto.encrypt(text, _MMDPAWN_KEY, _MMDPAWN_IV)

def mmdpawn_decrypt(text: str) -> str:
    return crypto.decrypt(urllib.parse.unquote(text), _MMDPAWN_KEY, _MMDPAWN_IV)