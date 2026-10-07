"""Overdue loans service functions.

The signatures below are the shared interface: the overdue router calls into
this module once the report ticket implements the bodies.
"""

from sqlalchemy.orm import Session

from app.schemas.loans import OverdueLoanRead


def list_overdue(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[OverdueLoanRead], int]:
    """Return a page of overdue open loans and the total number of matches."""

    raise NotImplementedError
