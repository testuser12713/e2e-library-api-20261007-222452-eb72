"""Member service functions.

The signatures below are the shared interface: the member router calls into this
module once the CRUD ticket implements the bodies.
"""

from sqlalchemy.orm import Session

from app.models import Member
from app.schemas.members import MemberCreate, MemberUpdate


def list_members(db: Session, *, limit: int = 20, offset: int = 0) -> tuple[list[Member], int]:
    """Return a page of members and the total number of matches."""

    raise NotImplementedError


def get_member(db: Session, member_id: int) -> Member:
    """Return a member by id or raise a not-found error."""

    raise NotImplementedError


def create_member(db: Session, data: MemberCreate) -> Member:
    """Persist a new member."""

    raise NotImplementedError


def update_member(db: Session, member_id: int, data: MemberUpdate) -> Member:
    """Update an existing member."""

    raise NotImplementedError


def delete_member(db: Session, member_id: int) -> None:
    """Delete a member."""

    raise NotImplementedError
