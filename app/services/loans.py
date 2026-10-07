"""Loan service functions.

The signatures below are the shared interface: the loan router calls into this
module once the lending-rules ticket implements the bodies.
"""

from sqlalchemy.orm import Session

from app.models import Loan
from app.schemas.loans import LoanCreate


def create_loan(db: Session, data: LoanCreate) -> Loan:
    """Create a loan if the lending rules allow it."""

    raise NotImplementedError


def return_loan(db: Session, loan_id: int) -> Loan:
    """Mark a loan as returned and free its copy."""

    raise NotImplementedError
