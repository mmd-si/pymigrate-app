import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from app.schemas.internal import AppMessage
from app.services import flash

logger = logging.getLogger(__name__)


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    logger.exception(exc)
    response = JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail},
        headers=exc.headers,
    )
    flash.send(response, AppMessage.error(exc.detail).dict())
    return response
