from __future__ import annotations

import os
from hmac import compare_digest
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response, status


LOCAL_APP_ENVS = {"", "local", "dev", "development", "test"}


def is_docs_enabled() -> bool:
    app_env = os.environ.get("APP_ENV", "local").strip().lower()

    if app_env in LOCAL_APP_ENVS:
        return True

    enable_docs = os.environ.get("ENABLE_DOCS", "false").strip().lower()
    return enable_docs in {"1", "true", "yes", "on"}


def docs_config() -> dict[str, str | None]:
    if is_docs_enabled():
        return {
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }

    return {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected_api_key = os.environ.get("API_KEY")
    if not expected_api_key:
        return

    if x_api_key is None or not compare_digest(x_api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def require_dashboard_api_key(x_api_key: str | None = Header(default=None)) -> None:
    protect_dashboard = os.environ.get("PROTECT_DASHBOARD", "false").strip().lower()
    if protect_dashboard not in {"1", "true", "yes", "on"}:
        return

    expected_api_key = os.environ.get("API_KEY")
    if (
        not expected_api_key
        or x_api_key is None
        or not compare_digest(x_api_key, expected_api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
