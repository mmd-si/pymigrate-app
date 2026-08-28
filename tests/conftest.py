import os

# Must run before any `app.*` import: `get_settings()` is evaluated at
# import time in app/config/db.py, app/services/auth.py (which also derives
# the MMDPawn AES key from mmdpawn_encrypt_pw at import time) and app/main.py.
# pytest imports conftest.py before collecting test modules in this tree, so
# setting env vars here (module level, not inside a fixture) runs early enough.
os.environ.setdefault('HOST', '0.0.0.0')
os.environ.setdefault('PORT', '3000')
os.environ.setdefault('ACCESS_CONTROL_ALLOW_ORIGINS', '*')
os.environ.setdefault('REMOTE_DB_DRIVER', 'mysql+aiomysql')
os.environ.setdefault('REMOTE_DB_HOST', 'localhost')
os.environ.setdefault('REMOTE_DB_PORT', '3306')
os.environ.setdefault('REMOTE_DB_USER', 'u')
os.environ.setdefault('REMOTE_DB_PASSWORD', 'p')
os.environ.setdefault('REMOTE_DB_NAME', 'db')
os.environ.setdefault('LOCAL_DB_DRIVER', 'postgresql+asyncpg')
os.environ.setdefault('LOCAL_DB_HOST', 'localhost')
os.environ.setdefault('LOCAL_DB_PORT', '5432')
os.environ.setdefault('LOCAL_DB_USER', 'u')
os.environ.setdefault('LOCAL_DB_PASSWORD', 'p')
os.environ.setdefault('LOCAL_DB_NAME', 'db')
os.environ.setdefault('MMDPAWN_ENCRYPT_PW', 'testpassword')
os.environ.setdefault('MMDPAWN_API_URL', 'http://mmdpawn.test')
os.environ.setdefault('TRUST_PROXY', 'False')
os.environ.setdefault('PYTHON_ENV', 'development')
os.environ.setdefault('LOG_LEVEL', 'info')

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_client_info, get_local_db, get_remote_db, require_session
from app.main import app
from app.schemas.internal import ClientInfo
from tests.support.builders import make_session


async def _override_local_db():
    yield AsyncMock()


async def _override_remote_db():
    yield AsyncMock()


def _override_client_info() -> ClientInfo:
    return ClientInfo(ip_address='127.0.0.1', user_agent='pytest')


@pytest.fixture
async def app_client():
    app.dependency_overrides[get_local_db] = _override_local_db
    app.dependency_overrides[get_remote_db] = _override_remote_db
    app.dependency_overrides[require_session] = lambda: make_session()
    app.dependency_overrides[get_client_info] = _override_client_info

    # Matches the old suite's TestClient(..., raise_server_exceptions=False):
    # Starlette's ServerErrorMiddleware always re-raises after sending the
    # handler's response, by design. Without this, an unhandled exception in
    # a route would propagate into the test instead of yielding the 500
    # response generic_exception_handler produced.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        yield client

    app.dependency_overrides.clear()
