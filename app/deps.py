"""Shared FastAPI dependencies."""

import secrets

from fastapi import Header

from app.config import get_settings
from app.db import get_db
from app.errors import AppError

__all__ = ["get_db", "require_api_key"]


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Reject a request whose ``X-API-Key`` does not match the configured key.

    An unset API key or a missing/wrong header value answers 401 with the
    unified error body.
    """

    settings = get_settings()
    if (
        not settings.api_key
        or not x_api_key
        or not secrets.compare_digest(x_api_key, settings.api_key)
    ):
        raise AppError(
            code="unauthorized",
            message="Missing or invalid API key",
            status=401,
        )
