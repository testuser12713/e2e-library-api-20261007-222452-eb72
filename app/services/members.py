"""Member service functions.

The signatures below are the shared interface the member router calls into.
Open-loan counts are derived from the ``loans`` table (a loan is open while
``zurueckgegeben_am`` is null), never from the denormalised member column.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Loan, Member
from app.schemas.members import MemberCreate, MemberRead, MemberUpdate


def _duplicate_email_error(email: str) -> AppError:
    """Build the unified 409 answer for an email that already exists."""

    return AppError(
        code="duplicate_email",
        message=f"A member with email '{email}' already exists",
        status=409,
        details=[{"field": "email", "message": "email is already in use"}],
    )


def _email_in_use(db: Session, email: str, *, exclude_id: int | None = None) -> bool:
    """Return whether another member already uses ``email``, ignoring case."""

    statement = select(Member.id).where(func.lower(Member.email) == email.lower())
    if exclude_id is not None:
        statement = statement.where(Member.id != exclude_id)
    return db.scalar(statement) is not None


def open_loan_count(db: Session, member_id: int) -> int:
    """Return the number of a member's loans that are still open."""

    return (
        db.scalar(
            select(func.count())
            .select_from(Loan)
            .where(Loan.member_id == member_id, Loan.zurueckgegeben_am.is_(None))
        )
        or 0
    )


def open_loan_counts(db: Session, member_ids: Sequence[int]) -> dict[int, int]:
    """Return open-loan counts for several members in one query."""

    if not member_ids:
        return {}
    rows = db.execute(
        select(Loan.member_id, func.count())
        .where(Loan.member_id.in_(member_ids), Loan.zurueckgegeben_am.is_(None))
        .group_by(Loan.member_id)
    ).all()
    return dict(rows)


def to_read(member: Member, offene_ausleihen: int) -> MemberRead:
    """Project an ORM member onto its read schema with an explicit count."""

    return MemberRead(
        id=member.id,
        name=member.name,
        email=member.email,
        mitglied_seit=member.mitglied_seit,
        offene_ausleihen=offene_ausleihen,
    )


def list_members(db: Session, *, limit: int = 20, offset: int = 0) -> tuple[list[Member], int]:
    """Return a page of members and the total number of matches.

    Members are sorted by name and then id.
    """

    total = db.scalar(select(func.count()).select_from(Member)) or 0
    members = list(
        db.scalars(
            select(Member).order_by(Member.name, Member.id).limit(limit).offset(offset)
        ).all()
    )
    return members, total


def get_member(db: Session, member_id: int) -> Member:
    """Return a member by id or raise a not-found error."""

    member = db.get(Member, member_id)
    if member is None:
        raise AppError(
            code="not_found",
            message=f"Member {member_id} not found",
            status=404,
        )
    return member


def create_member(db: Session, data: MemberCreate) -> Member:
    """Persist a new member, rejecting a duplicate email with 409."""

    email = str(data.email)
    if _email_in_use(db, email):
        raise _duplicate_email_error(email)

    member = Member(
        name=data.name,
        email=email,
        mitglied_seit=data.mitglied_seit,
        offene_ausleihen=0,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_member(db: Session, member_id: int, data: MemberUpdate) -> Member:
    """Update an existing member's fields, rejecting a duplicate email with 409."""

    member = get_member(db, member_id)
    updates = data.model_dump(exclude_unset=True)

    if "email" in updates:
        email = str(updates["email"])
        if _email_in_use(db, email, exclude_id=member_id):
            raise _duplicate_email_error(email)
        member.email = email

    if "name" in updates:
        member.name = updates["name"]

    if "mitglied_seit" in updates:
        member.mitglied_seit = updates["mitglied_seit"]

    db.commit()
    db.refresh(member)
    return member


def delete_member(db: Session, member_id: int) -> None:
    """Delete a member, or raise not-found when the id is unknown."""

    member = get_member(db, member_id)
    db.delete(member)
    db.commit()
