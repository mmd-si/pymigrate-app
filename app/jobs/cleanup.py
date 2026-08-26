from sqlalchemy import delete

from app.config.db import LocalSession
from app.core.utils import utcnow
from app.models.local import Session


async def remove_expired_sessions():
    async with LocalSession() as db:
        stmt = delete(Session).where(Session.expires_at <= utcnow())
        await db.execute(stmt)
        await db.commit()