"""Overdue loans report route."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.common import Page, PaginationParams
from app.schemas.loans import OverdueLoanRead

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/overdue", response_model=Page[OverdueLoanRead])
def list_overdue(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
) -> Page[OverdueLoanRead]:
    """List open loans whose due date is before today."""

    raise HTTPException(status_code=501, detail="overdue #5 implements this")
