"""Tests for the loan creation, return and lending rules (AC-07 .. AC-11, AC-14)."""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, func, or_, select

from app.db import SessionLocal
from app.models import Book, Loan, Member
from app.services.loans import LOAN_LIMIT, LOAN_PERIOD_DAYS


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _open_loan_count(book_id: int, member_id: int | None = None) -> int:
    with SessionLocal() as db:
        statement = (
            select(func.count())
            .select_from(Loan)
            .where(Loan.zurueckgegeben_am.is_(None), Loan.book_id == book_id)
        )
        if member_id is not None:
            statement = statement.where(Loan.member_id == member_id)
        return db.scalar(statement) or 0


def _book_verfuegbar(book_id: int) -> int | None:
    with SessionLocal() as db:
        book = db.get(Book, book_id)
        return None if book is None else book.verfuegbar


def _member_offene_ausleihen(member_id: int) -> int | None:
    with SessionLocal() as db:
        member = db.get(Member, member_id)
        return None if member is None else member.offene_ausleihen


@pytest.fixture
def library():
    """Provision books and members directly in the DB for the loan tests."""

    created_books: list[int] = []
    created_members: list[int] = []

    def add_book(*, exemplare: int = 1) -> int:
        with SessionLocal() as db:
            book = Book(
                titel=_unique("Titel"),
                autor=_unique("Autor"),
                isbn=_unique("isbn"),
                erscheinungsjahr=2000,
                exemplare=exemplare,
                verfuegbar=exemplare,
            )
            db.add(book)
            db.commit()
            db.refresh(book)
            created_books.append(book.id)
            return book.id

    def add_member() -> int:
        with SessionLocal() as db:
            member = Member(
                name=_unique("Name"),
                email=f"{_unique('mail')}@example.com",
                mitglied_seit=date.today(),
                offene_ausleihen=0,
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            created_members.append(member.id)
            return member.id

    yield SimpleNamespace(add_book=add_book, add_member=add_member)

    with SessionLocal() as db:
        conditions = []
        if created_books:
            conditions.append(Loan.book_id.in_(created_books))
        if created_members:
            conditions.append(Loan.member_id.in_(created_members))
        if conditions:
            db.execute(delete(Loan).where(or_(*conditions)))
        if created_books:
            db.execute(delete(Book).where(Book.id.in_(created_books)))
        if created_members:
            db.execute(delete(Member).where(Member.id.in_(created_members)))
        db.commit()


def _assert_error(response, status_code: int, code: str) -> dict:
    """Assert the unified error envelope and return its ``error`` object."""

    assert response.status_code == status_code, response.text
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert "details" in error
    return error


def test_create_loan_sets_dates_and_reduces_availability(client, auth_headers, library):
    """AC-07: a loan is created for today with a 14-day due date."""

    book_id = library.add_book(exemplare=2)
    member_id = library.add_member()

    response = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": member_id},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    today = date.today()
    assert body["book_id"] == book_id
    assert body["member_id"] == member_id
    assert body["ausgeliehen_am"] == today.isoformat()
    assert body["faellig_am"] == (today + timedelta(days=LOAN_PERIOD_DAYS)).isoformat()
    assert body["zurueckgegeben_am"] is None

    # exactly one copy less free, both in the counter and in the open loans
    assert _book_verfuegbar(book_id) == 1
    assert _open_loan_count(book_id) == 1
    assert _member_offene_ausleihen(member_id) == 1


def test_create_loan_respects_member_limit(client, auth_headers, library):
    """AC-08: a fourth open loan for one member is rejected with 409."""

    book_id = library.add_book(exemplare=10)
    member_id = library.add_member()

    for _ in range(LOAN_LIMIT):
        response = client.post(
            "/loans",
            json={"book_id": book_id, "member_id": member_id},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": member_id},
        headers=auth_headers,
    )
    _assert_error(response, 409, "loan_limit_reached")
    assert _open_loan_count(book_id, member_id) == LOAN_LIMIT
    assert _member_offene_ausleihen(member_id) == LOAN_LIMIT


def test_create_loan_rejects_when_no_copy_available(client, auth_headers, library):
    """AC-09: all copies lent out -> 409; after a return one copy is free again."""

    book_id = library.add_book(exemplare=1)
    first_member = library.add_member()
    second_member = library.add_member()

    first = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": first_member},
        headers=auth_headers,
    )
    assert first.status_code == 201, first.text
    loan_id = first.json()["id"]

    blocked = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": second_member},
        headers=auth_headers,
    )
    error = _assert_error(blocked, 409, "no_copy_available")
    assert error["details"] is None
    assert _open_loan_count(book_id) == 1

    returned = client.post(f"/loans/{loan_id}/return", headers=auth_headers)
    assert returned.status_code == 200, returned.text
    assert _book_verfuegbar(book_id) == 1

    retry = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": second_member},
        headers=auth_headers,
    )
    assert retry.status_code == 201, retry.text
    assert _open_loan_count(book_id) == 1


def test_create_loan_unknown_ids_and_validation(client, auth_headers, library):
    """AC-10: unknown ids -> 404, missing/invalid fields -> 422 with the field."""

    member_id = library.add_member()
    book_id = library.add_book()

    unknown_book = client.post(
        "/loans",
        json={"book_id": 9_999_999, "member_id": member_id},
        headers=auth_headers,
    )
    _assert_error(unknown_book, 404, "not_found")

    unknown_member = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": 9_999_999},
        headers=auth_headers,
    )
    _assert_error(unknown_member, 404, "not_found")

    missing = client.post("/loans", json={}, headers=auth_headers)
    error = _assert_error(missing, 422, "validation_error")
    fields = {detail["field"] for detail in error["details"]}
    assert "book_id" in fields
    assert "member_id" in fields

    wrong_type = client.post(
        "/loans",
        json={"book_id": "not-an-int", "member_id": member_id},
        headers=auth_headers,
    )
    error = _assert_error(wrong_type, 422, "validation_error")
    assert any(detail["field"] == "book_id" for detail in error["details"])


def test_return_loan_frees_copy_and_rejects_double_return(client, auth_headers, library):
    """AC-11: returning stamps today and a second call answers 409."""

    book_id = library.add_book(exemplare=1)
    member_id = library.add_member()
    loan = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": member_id},
        headers=auth_headers,
    )
    assert loan.status_code == 201, loan.text
    loan_id = loan.json()["id"]

    response = client.post(f"/loans/{loan_id}/return", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == loan_id
    assert body["zurueckgegeben_am"] == date.today().isoformat()
    assert _open_loan_count(book_id) == 0
    assert _book_verfuegbar(book_id) == 1
    assert _member_offene_ausleihen(member_id) == 0

    again = client.post(f"/loans/{loan_id}/return", headers=auth_headers)
    _assert_error(again, 409, "already_returned")


def test_return_unknown_loan_is_not_found(client, auth_headers):
    """A return for an unknown loan id answers 404 in the unified format."""

    response = client.post("/loans/9_999_999/return", headers=auth_headers)
    _assert_error(response, 404, "not_found")


def test_error_bodies_are_unified(client, auth_headers, library):
    """AC-14: 401, 404, 409 and 422 all use the same error envelope."""

    book_id = library.add_book(exemplare=1)
    member_id = library.add_member()

    unauthorized_create = client.post("/loans", json={"book_id": book_id, "member_id": member_id})
    _assert_error(unauthorized_create, 401, "unauthorized")

    unauthorized_return = client.post("/loans/1/return")
    _assert_error(unauthorized_return, 401, "unauthorized")

    not_found = client.post(
        "/loans",
        json={"book_id": 9_999_999, "member_id": member_id},
        headers=auth_headers,
    )
    _assert_error(not_found, 404, "not_found")

    validation = client.post("/loans", json={}, headers=auth_headers)
    _assert_error(validation, 422, "validation_error")

    created = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": member_id},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    booked_member = library.add_member()
    conflict = client.post(
        "/loans",
        json={"book_id": book_id, "member_id": booked_member},
        headers=auth_headers,
    )
    _assert_error(conflict, 409, "no_copy_available")
