"""Loan request and response schemas."""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.books import BookRead
from app.schemas.members import MemberRead


class LoanCreate(BaseModel):
    """Payload for creating a loan."""

    book_id: int
    member_id: int


class LoanRead(BaseModel):
    """A loan as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    member_id: int
    ausgeliehen_am: date
    faellig_am: date
    zurueckgegeben_am: date | None = None


class OverdueLoanRead(BaseModel):
    """An overdue open loan with its book, member and days overdue."""

    loan_id: int
    book: BookRead
    member: MemberRead
    ausgeliehen_am: date
    faellig_am: date
    tage_ueberfaellig: int
