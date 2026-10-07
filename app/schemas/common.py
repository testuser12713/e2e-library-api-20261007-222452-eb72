"""Shared schema building blocks: pagination and the unified error envelope."""

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """A single page of results together with the total number of matches."""

    items: list[T]
    total: int
    limit: int
    offset: int


class PaginationParams(BaseModel):
    """Validated pagination query parameters (limit at most 100)."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ErrorDetail(BaseModel):
    """One field-level error entry."""

    field: str
    message: str


class ErrorBody(BaseModel):
    """The ``error`` object of the unified error format."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorEnvelope(BaseModel):
    """The unified error response body used by every error path."""

    error: ErrorBody
