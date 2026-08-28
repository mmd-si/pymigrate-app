import logging
import time
from fastapi import Request
from app.dependencies import get_client_info

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    client = get_client_info(request)

    logger.info(
        '%s %s -> %s (%.1fms) client=%s',
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        client.ip_address,
    )
    return response
