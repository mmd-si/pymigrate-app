"""Async wrapper around a blocking ``xmlrpc.client`` connection to Odoo.

Ported from ``pymigrate/migrate-worker/app/odoo/odoo_connection.py``. There is no
async XML-RPC library, so authentication and every ``execute_kw`` call are pushed
to a worker thread with ``asyncio.to_thread``. One instance per ``OdooContext``
(not a global singleton) — a ``ServerProxy`` is not safe for concurrent use, and
drains build their own context.
"""

import asyncio
import logging
from http.client import HTTPConnection, HTTPSConnection
from xmlrpc.client import ServerProxy, Transport

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class _TimeoutTransport(Transport):
    def __init__(self, timeout: int, secure: bool = False):
        super().__init__()
        self._timeout = timeout
        self._secure = secure

    def make_connection(self, host):
        if self._connection and self._connection[0] == host:
            return self._connection[1]
        conn_class = HTTPSConnection if self._secure else HTTPConnection
        conn = conn_class(host, timeout=self._timeout)
        self._connection = (host, conn)
        return conn


class OdooConnection:
    def __init__(self, settings: Settings):
        self._url = settings.odoo_url
        self._db = settings.odoo_db
        self._user = settings.odoo_user
        self._password = settings.odoo_password
        self._timeout = settings.odoo_timeout

        self._models: ServerProxy | None = None
        self._args: tuple | None = None
        self._lock = asyncio.Lock()

    def _connect(self) -> None:
        secure = self._url.strip().startswith('https')
        common = ServerProxy(
            f'{self._url}/xmlrpc/2/common',
            transport=_TimeoutTransport(self._timeout, secure=secure),
        )
        uid = common.authenticate(self._db, self._user, self._password, {})
        if not uid:
            raise ConnectionError('Odoo XML-RPC authentication failed: no uid returned.')
        self._models = ServerProxy(
            f'{self._url}/xmlrpc/2/object',
            transport=_TimeoutTransport(self._timeout, secure=secure),
        )
        self._args = (self._db, uid, self._password)
        logger.info('authenticated with Odoo XML-RPC (uid=%s)', uid)

    async def ensure(self) -> None:
        if self._models is not None:
            return
        async with self._lock:
            if self._models is not None:
                return
            await asyncio.to_thread(self._connect)

    async def execute_kw(self, model: str, method: str, *args, **kwargs):
        await self.ensure()
        assert self._models is not None and self._args is not None
        return await asyncio.to_thread(
            self._models.execute_kw, *self._args, model, method, *args, **kwargs
        )
