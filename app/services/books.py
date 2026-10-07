"""Book service functions.

The signatures below are the shared interface: the book router calls into this
module once the CRUD ticket implements the bodies.
"""

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Book, Loan
from app.schemas.books import BookCreate, BookUpdate


def open_loan_counts(db: Session, book_ids: Sequence[int]) -> dict[int, int]:
    """Return the number of open (not yet returned) loans per book id."""

    if not book_ids:
        return {}
    rows = db.execute(
        select(Loan.book_id, func.count())
        .where(Loan.book_id.in_(book_ids), Loan.zurueckgegeben_am.is_(None))
        .group_by(Loan.book_id)
    ).all()
    return {book_id: int(count) for book_id, count in rows}


def _escape_like(value: str) -> str:
    """Escape the SQL ``LIKE`` wildcards so a search term is matched literally."""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_books(
    db: Session,
    *,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Book], int]:
    """Return a page of books and the total number of matches.

    ``q`` filters case-insensitively on a substring of the title OR the author.
    Results are ordered stably by title and then by id.
    """

    statement = select(Book)
    count_statement = select(func.count()).select_from(Book)

    if q is not None and q.strip() != "":
        pattern = f"%{_escape_like(q.lower())}%"
        condition = or_(
            func.lower(Book.titel).like(pattern, escape="\\"),
            func.lower(Book.autor).like(pattern, escape="\\"),
        )
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    total = int(db.scalar(count_statement) or 0)
    statement = statement.order_by(Book.titel, Book.id).limit(limit).offset(offset)
    books = list(db.scalars(statement).all())
    return books, total


def get_book(db: Session, book_id: int) -> Book:
    """Return a book by id or raise a not-found error."""

    book = db.get(Book, book_id)
    if book is None:
        raise AppError(
            code="not_found",
            message=f"Book {book_id} was not found",
            status=404,
        )
    return book


def _duplicate_isbn_error(isbn: str) -> AppError:
    """Build the unified duplicate-ISBN error."""

    return AppError(
        code="duplicate_isbn",
        message=f"A book with ISBN {isbn} already exists",
        status=409,
    )


def create_book(db: Session, data: BookCreate) -> Book:
    """Persist a new book.

    A book whose ISBN already exists raises a duplicate error and inserts
    nothing.
    """

    existing = db.scalar(select(Book).where(Book.isbn == data.isbn))
    if existing is not None:
        raise _duplicate_isbn_error(data.isbn)

    book = Book(
        titel=data.titel,
        autor=data.autor,
        isbn=data.isbn,
        erscheinungsjahr=data.erscheinungsjahr,
        exemplare=data.exemplare,
        verfuegbar=data.exemplare,
    )
    db.add(book)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_isbn_error(data.isbn) from exc
    db.refresh(book)
    return book


def update_book(db: Session, book_id: int, data: BookUpdate) -> Book:
    """Update an existing book.

    Only the fields present in ``data`` are changed.  Changing the ISBN to one
    that belongs to another book raises a duplicate error.
    """

    book = get_book(db, book_id)
    changes = data.model_dump(exclude_unset=True)

    new_isbn = changes.get("isbn")
    if new_isbn is not None and new_isbn != book.isbn:
        duplicate = db.scalar(select(Book).where(Book.isbn == new_isbn, Book.id != book.id))
        if duplicate is not None:
            raise _duplicate_isbn_error(new_isbn)

    for field, value in changes.items():
        setattr(book, field, value)

    if "exemplare" in changes:
        open_loans = open_loan_counts(db, [book.id]).get(book.id, 0)
        book.verfuegbar = max(0, book.exemplare - open_loans)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if new_isbn is not None:
            raise _duplicate_isbn_error(new_isbn) from exc
        raise
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    """Delete a book that has no open loans."""

    book = get_book(db, book_id)
    open_loans = open_loan_counts(db, [book.id]).get(book.id, 0)
    if open_loans > 0:
        raise AppError(
            code="book_has_open_loans",
            message="The book still has open loans",
            status=409,
        )
    db.delete(book)
    db.commit()
