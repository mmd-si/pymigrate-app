import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from app import api
from app.config.db import local_engine, remote_engine
from app.config.settings import get_settings
from app.core.handlers import generic_exception_handler, http_exception_handler
from app.core.middleware import log_requests
from app.core.scheduler import shutdown_scheduler, start_scheduler


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()
    await local_engine.dispose()
    await remote_engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.middleware('http')(log_requests)
app.include_router(api.router)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


if __name__ == '__main__':
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level)
