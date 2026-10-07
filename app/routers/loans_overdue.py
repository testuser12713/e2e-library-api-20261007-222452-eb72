"""Overdue loans report route."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.common import Page, PaginationParams
from app.schemas.loans import OverdueLoanRead
from app.services.overdue import list_overdue as list_overdue_service

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/overdue", response_model=Page[OverdueLoanRead])
def list_overdue(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[OverdueLoanRead]:
    """List open loans whose due date is before today."""

    items, total = list_overdue_service(
        db,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page[OverdueLoanRead](
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
