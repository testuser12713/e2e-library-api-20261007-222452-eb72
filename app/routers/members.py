"""Member routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.schemas.common import Page, PaginationParams
from app.schemas.members import MemberCreate, MemberRead, MemberUpdate

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=Page[MemberRead])
def list_members(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[MemberRead]:
    """List members."""

    raise HTTPException(status_code=501, detail="members #3 implements this")


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

    raise HTTPException(status_code=501, detail="members #3 implements this")


@router.get("/{member_id}", response_model=MemberRead)
def get_member(
    member_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    """Return a single member by id."""

    raise HTTPException(status_code=501, detail="members #3 implements this")


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

    raise HTTPException(status_code=501, detail="members #3 implements this")


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

    raise HTTPException(status_code=501, detail="members #3 implements this")


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

    raise HTTPException(status_code=501, detail="members #3 implements this")
