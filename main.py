from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.core.security import add_security_headers, docs_config, get_cors_origins
from app.database.health import initialize_database
from app.database.urls import database_backend, redact_database_url

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Database backend active: %s (%s)",
        database_backend(settings.database.url),
        redact_database_url(settings.database.url),
    )
    initialize_database()
    yield


app = FastAPI(title=settings.app.name, lifespan=lifespan, **docs_config())
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_security_headers(app)
app.include_router(api_router)
