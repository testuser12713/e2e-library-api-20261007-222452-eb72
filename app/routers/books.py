"""Book routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.schemas.books import BookCreate, BookRead, BookUpdate
from app.schemas.common import Page, PaginationParams

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=Page[BookRead])
def list_books(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    q: Annotated[str | None, Query()] = None,
) -> Page[BookRead]:
    """List books, optionally filtered by a case-insensitive substring search."""

    raise HTTPException(status_code=501, detail="books #2 implements this")


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_book(
    payload: BookCreate,
    db: Annotated[Session, Depends(get_db)],
) -> BookRead:
    """Create a new book."""

    raise HTTPException(status_code=501, detail="books #2 implements this")


@router.get("/{book_id}", response_model=BookRead)
def get_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> BookRead:
    """Return a single book by id."""

    raise HTTPException(status_code=501, detail="books #2 implements this")


@router.put(
    "/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_api_key)],
)
def replace_book(
    book_id: int,
    payload: BookUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> BookRead:
    """Replace a book's fields."""

    raise HTTPException(status_code=501, detail="books #2 implements this")


@router.patch(
    "/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_api_key)],
)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> BookRead:
    """Update selected fields of a book."""

    raise HTTPException(status_code=501, detail="books #2 implements this")


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
def delete_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a book that has no open loans."""

    raise HTTPException(status_code=501, detail="books #2 implements this")
