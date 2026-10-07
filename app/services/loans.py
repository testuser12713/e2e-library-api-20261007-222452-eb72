"""Loan service functions.

Lending rules enforced here:

* the book and the member must exist;
* a member may hold at most :data:`LOAN_LIMIT` open loans at a time;
* a book may only be lent while fewer than ``exemplare`` copies are open;
* a loan runs for :data:`LOAN_PERIOD_DAYS` days from the lending date.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Book, Loan, Member
from app.schemas.loans import LoanCreate

#: A member may hold at most this many open loans at once.
LOAN_LIMIT = 3

#: How many days a loan runs until it is due.
LOAN_PERIOD_DAYS = 14


def _open_loans_count(db: Session, **filters: int) -> int:
    """Count open loans (not yet returned), optionally filtered by a column."""

    statement = select(func.count()).select_from(Loan).where(Loan.zurueckgegeben_am.is_(None))
    for column, value in filters.items():
        statement = statement.where(getattr(Loan, column) == value)
    return db.scalar(statement) or 0


def create_loan(db: Session, data: LoanCreate) -> Loan:
    """Create a loan if the lending rules allow it."""

    book = db.get(Book, data.book_id)
    if book is None:
        raise AppError(
            code="not_found",
            message=f"Book {data.book_id} not found",
            status=404,
        )

    member = db.get(Member, data.member_id)
    if member is None:
        raise AppError(
            code="not_found",
            message=f"Member {data.member_id} not found",
            status=404,
        )

    if _open_loans_count(db, member_id=member.id) >= LOAN_LIMIT:
        raise AppError(
            code="loan_limit_reached",
            message=f"Member {member.id} already has {LOAN_LIMIT} open loans",
            status=409,
        )

    if _open_loans_count(db, book_id=book.id) >= book.exemplare:
        raise AppError(
            code="no_copy_available",
            message=f"No free copy of book {book.id} available",
            status=409,
        )

    today = date.today()
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        ausgeliehen_am=today,
        faellig_am=today + timedelta(days=LOAN_PERIOD_DAYS),
        zurueckgegeben_am=None,
    )
    db.add(loan)

    book.verfuegbar = max(book.verfuegbar - 1, 0)
    member.offene_ausleihen = member.offene_ausleihen + 1

    db.commit()
    db.refresh(loan)
    return loan


def return_loan(db: Session, loan_id: int) -> Loan:
    """Mark a loan as returned and free its copy."""

    loan = db.get(Loan, loan_id)
    if loan is None:
        raise AppError(
            code="not_found",
            message=f"Loan {loan_id} not found",
            status=404,
        )

    if loan.zurueckgegeben_am is not None:
        raise AppError(
            code="already_returned",
            message=f"Loan {loan_id} was already returned",
            status=409,
        )

    loan.zurueckgegeben_am = date.today()

    book = db.get(Book, loan.book_id)
    if book is not None:
        book.verfuegbar = min(book.verfuegbar + 1, book.exemplare)

    member = db.get(Member, loan.member_id)
    if member is not None:
        member.offene_ausleihen = max(member.offene_ausleihen - 1, 0)

    db.commit()
    db.refresh(loan)
    return loan
