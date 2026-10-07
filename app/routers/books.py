"""Book routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import Book
from app.schemas.books import BookCreate, BookRead, BookUpdate
from app.schemas.common import Page, PaginationParams
from app.services import books as book_service

router = APIRouter(prefix="/books", tags=["books"])


def _to_read(book: Book, open_loans: int) -> BookRead:
    """Build a ``BookRead`` with its free copy count derived from open loans."""

    return BookRead(
        id=book.id,
        titel=book.titel,
        autor=book.autor,
        isbn=book.isbn,
        erscheinungsjahr=book.erscheinungsjahr,
        exemplare=book.exemplare,
        verfuegbar=book.exemplare - open_loans,
    )


def _single_read(db: Session, book: Book) -> BookRead:
    """Serialise one book, counting its open loans."""

    open_loans = book_service.open_loan_counts(db, [book.id]).get(book.id, 0)
    return _to_read(book, open_loans)


@router.get("", response_model=Page[BookRead])
def list_books(
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    q: Annotated[str | None, Query()] = None,
) -> Page[BookRead]:
    """List books, optionally filtered by a case-insensitive substring search."""

    books, total = book_service.list_books(
        db,
        q=q,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    counts = book_service.open_loan_counts(db, [book.id for book in books])
    items = [_to_read(book, counts.get(book.id, 0)) for book in books]
    return Page[BookRead](
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


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

    book = book_service.create_book(db, payload)
    return _single_read(db, book)


@router.get("/{book_id}", response_model=BookRead)
def get_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> BookRead:
    """Return a single book by id."""

    book = book_service.get_book(db, book_id)
    return _single_read(db, book)


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

    book = book_service.update_book(db, book_id, payload)
    return _single_read(db, book)


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

    book = book_service.update_book(db, book_id, payload)
    return _single_read(db, book)


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

    book_service.delete_book(db, book_id)
