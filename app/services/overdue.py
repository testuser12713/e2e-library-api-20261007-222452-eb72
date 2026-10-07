"""Overdue loans service functions.

The signatures below are the shared interface: the overdue router calls into
this module once the report ticket implements the bodies.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Loan
from app.schemas.books import BookRead
from app.schemas.loans import OverdueLoanRead
from app.schemas.members import MemberRead


def list_overdue(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[OverdueLoanRead], int]:
    """Return a page of overdue open loans and the total number of matches.

    An overdue loan is open (``zurueckgegeben_am`` is null) and its due date
    lies strictly before today.  The result is ordered by due date and id.
    """

    today = date.today()

    conditions = (
        Loan.zurueckgegeben_am.is_(None),
        Loan.faellig_am < today,
    )

    total = db.scalar(select(func.count()).select_from(Loan).where(*conditions)) or 0

    stmt = (
        select(Loan)
        .options(joinedload(Loan.book), joinedload(Loan.member))
        .where(*conditions)
        .order_by(Loan.faellig_am, Loan.id)
        .limit(limit)
        .offset(offset)
    )
    loans = db.scalars(stmt).all()

    items = [
        OverdueLoanRead(
            loan_id=loan.id,
            book=BookRead.model_validate(loan.book),
            member=MemberRead.model_validate(loan.member),
            ausgeliehen_am=loan.ausgeliehen_am,
            faellig_am=loan.faellig_am,
            tage_ueberfaellig=(today - loan.faellig_am).days,
        )
        for loan in loans
    ]
    return items, total
