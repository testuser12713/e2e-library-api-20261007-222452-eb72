"""Book request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_YEAR = 2100
MIN_YEAR = 1450


def _validate_isbn(value: str) -> str:
    """Validate that ``value`` looks like an ISBN-10 or ISBN-13.

    Hyphens and spaces are allowed; the check verifies length and character set
    after normalisation.
    """

    normalized = value.replace("-", "").replace(" ", "").upper()
    if len(normalized) == 10:
        if not normalized[:9].isdigit() or not (normalized[9].isdigit() or normalized[9] == "X"):
            raise ValueError("isbn must be a valid ISBN-10 or ISBN-13")
        return value
    if len(normalized) == 13:
        if not normalized.isdigit():
            raise ValueError("isbn must be a valid ISBN-10 or ISBN-13")
        return value
    raise ValueError("isbn must be a valid ISBN-10 or ISBN-13")


class BookCreate(BaseModel):
    """Payload for creating a book."""

    titel: str = Field(min_length=1)
    autor: str = Field(min_length=1)
    isbn: str
    erscheinungsjahr: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    exemplare: int = Field(default=1, ge=1)

    _check_isbn = field_validator("isbn")(_validate_isbn)


class BookUpdate(BaseModel):
    """Payload for updating a book; every field is optional."""

    titel: str | None = Field(default=None, min_length=1)
    autor: str | None = Field(default=None, min_length=1)
    isbn: str | None = None
    erscheinungsjahr: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    exemplare: int | None = Field(default=None, ge=1)

    @field_validator("isbn")
    @classmethod
    def _check_isbn(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_isbn(value)


class BookRead(BaseModel):
    """A book as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titel: str
    autor: str
    isbn: str
    erscheinungsjahr: int | None = None
    exemplare: int
    verfuegbar: int
