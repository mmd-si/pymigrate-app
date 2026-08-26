from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from app.config.settings import get_settings

settings = get_settings()

local_engine: AsyncEngine = create_async_engine(settings.local_db_url)
remote_engine: AsyncEngine = create_async_engine(settings.remote_db_url)

LocalSession = async_sessionmaker(local_engine, expire_on_commit=False)
RemoteSession = async_sessionmaker(remote_engine, expire_on_commit=False)
