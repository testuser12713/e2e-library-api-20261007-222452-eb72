"""Member routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import Member
from app.schemas.common import Page, PaginationParams
from app.schemas.members import MemberCreate, MemberRead, MemberUpdate
from app.services import members as member_service

router = APIRouter(prefix="/members", tags=["members"])


def _read(db: Session, member: Member) -> MemberRead:
    """Serialise one member together with its current open-loan count."""

    return member_service.to_read(member, member_service.open_loan_count(db, member.id))


@router.get("", response_model=Page[MemberRead])
def list_members(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[MemberRead]:
    """List members in a pagination envelope, sorted by name then id."""

    members, total = member_service.list_members(
        db, limit=pagination.limit, offset=pagination.offset
    )
    counts = member_service.open_loan_counts(db, [member.id for member in members])
    items = [member_service.to_read(member, counts.get(member.id, 0)) for member in members]
    return Page[MemberRead](
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post(
    "",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_member(
    payload: MemberCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    """Create a new member."""

    member = member_service.create_member(db, payload)
    return _read(db, member)


@router.get("/{member_id}", response_model=MemberRead)
def get_member(
    member_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    """Return a single member by id."""

    member = member_service.get_member(db, member_id)
    return _read(db, member)


@router.put(
    "/{member_id}",
    response_model=MemberRead,
    dependencies=[Depends(require_api_key)],
)
def replace_member(
    member_id: int,
    payload: MemberUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    """Replace a member's fields."""

    member = member_service.update_member(db, member_id, payload)
    return _read(db, member)


@router.patch(
    "/{member_id}",
    response_model=MemberRead,
    dependencies=[Depends(require_api_key)],
)
def update_member(
    member_id: int,
    payload: MemberUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    """Update selected fields of a member."""

    member = member_service.update_member(db, member_id, payload)
    return _read(db, member)


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
def delete_member(
    member_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a member."""

    member_service.delete_member(db, member_id)
