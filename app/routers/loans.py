"""Loan routes for creating and returning loans."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.schemas.loans import LoanCreate, LoanRead

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post(
    "",
    response_model=LoanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_loan(
    payload: LoanCreate,
    db: Annotated[Session, Depends(get_db)],
) -> LoanRead:
    """Create a loan if the member and the book allow it."""

    raise HTTPException(status_code=501, detail="loans #4 implements this")


@router.post(
    "/{loan_id}/return",
    response_model=LoanRead,
    dependencies=[Depends(require_api_key)],
)
def return_loan(
    loan_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> LoanRead:
    """Mark a loan as returned and free its copy."""

    raise HTTPException(status_code=501, detail="loans #4 implements this")
