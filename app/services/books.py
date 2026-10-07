"""Book service functions.

The signatures below are the shared interface: the book router calls into this
module once the CRUD ticket implements the bodies.
"""

from sqlalchemy.orm import Session

from app.models import Book
from app.schemas.books import BookCreate, BookUpdate


def list_books(
    db: Session,
    *,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Book], int]:
    """Return a page of books and the total number of matches."""

    raise NotImplementedError


def get_book(db: Session, book_id: int) -> Book:
    """Return a book by id or raise a not-found error."""

    raise NotImplementedError


def create_book(db: Session, data: BookCreate) -> Book:
    """Persist a new book."""

    raise NotImplementedError


def update_book(db: Session, book_id: int, data: BookUpdate) -> Book:
    """Update an existing book."""

    raise NotImplementedError


def delete_book(db: Session, book_id: int) -> None:
    """Delete a book that has no open loans."""

    raise NotImplementedError
