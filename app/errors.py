"""Unified error handling.

Every error answer has the same JSON body::

    {"error": {"code": str, "message": str, "details": [...] | null}}
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Location prefixes FastAPI puts in front of the real field name.
_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


class AppError(Exception):
    """A domain error carrying the code, status and optional field details."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details


def error_payload(
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the unified error body."""

    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the unified handlers for AppError, validation and crashes."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[dict[str, str]] = []
        for item in exc.errors():
            location = [str(part) for part in item.get("loc", ())]
            if location and location[0] in _LOCATION_PREFIXES:
                location = location[1:]
            details.append(
                {
                    "field": ".".join(location),
                    "message": item.get("msg", "invalid value"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=error_payload("validation_error", "Validation failed", details),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_error", "Internal server error"),
        )
