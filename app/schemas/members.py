"""Member request and response schemas."""

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MemberCreate(BaseModel):
    """Payload for creating a member."""

    name: str = Field(min_length=1)
    email: EmailStr
    mitglied_seit: date = Field(default_factory=date.today)


class MemberUpdate(BaseModel):
    """Payload for updating a member; every field is optional."""

    name: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    mitglied_seit: date | None = None


class MemberRead(BaseModel):
    """A member as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    mitglied_seit: date
    offene_ausleihen: int
