"""Tests for the overdue loans report (AC-12)."""

from datetime import date, timedelta

import pytest

from app.db import SessionLocal
from app.models import Book, Loan, Member


@pytest.fixture
def seed_book_member():
    """Create one book and one member, and remove them afterwards."""

    today = date.today()
    db = SessionLocal()
    try:
        book = Book(
            titel="Der Prozess",
            autor="Franz Kafka",
            isbn="978-3-16-148410-0",
            erscheinungsjahr=1925,
            exemplare=5,
            verfuegbar=5,
        )
        member = Member(
            name="Anna Beispiel",
            email="anna.beispiel@example.org",
            mitglied_seit=today,
            offene_ausleihen=0,
        )
        db.add_all([book, member])
        db.commit()
        book_id, member_id = book.id, member.id
    finally:
        db.close()

    yield book_id, member_id

    db = SessionLocal()
    try:
        db.query(Loan).filter(Loan.book_id == book_id, Loan.member_id == member_id).delete()
        db.query(Book).filter(Book.id == book_id).delete()
        db.query(Member).filter(Member.id == member_id).delete()
        db.commit()
    finally:
        db.close()


def _add_loan(
    book_id: int,
    member_id: int,
    *,
    ausgeliehen_am: date,
    faellig_am: date,
    zurueckgegeben_am: date | None = None,
) -> int:
    """Insert one loan directly and return its id."""

    db = SessionLocal()
    try:
        loan = Loan(
            book_id=book_id,
            member_id=member_id,
            ausgeliehen_am=ausgeliehen_am,
            faellig_am=faellig_am,
            zurueckgegeben_am=zurueckgegeben_am,
        )
        db.add(loan)
        db.commit()
        return loan.id
    finally:
        db.close()


def test_overdue_excludes_returned_and_not_yet_due(client, seed_book_member):
    """Only open loans past their due date are listed (AC-12)."""

    book_id, member_id = seed_book_member
    today = date.today()

    overdue_id = _add_loan(
        book_id,
        member_id,
        ausgeliehen_am=today - timedelta(days=20),
        faellig_am=today - timedelta(days=6),
    )
    _add_loan(
        book_id,
        member_id,
        ausgeliehen_am=today - timedelta(days=20),
        faellig_am=today - timedelta(days=6),
        zurueckgegeben_am=today - timedelta(days=1),
    )
    _add_loan(
        book_id,
        member_id,
        ausgeliehen_am=today,
        faellig_am=today + timedelta(days=14),
    )

    response = client.get("/loans/overdue")
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert [item["loan_id"] for item in body["items"]] == [overdue_id]

    entry = body["items"][0]
    assert entry["book"]["id"] == book_id
    assert entry["book"]["titel"] == "Der Prozess"
    assert entry["member"]["id"] == member_id
    assert entry["member"]["name"] == "Anna Beispiel"
    assert entry["ausgeliehen_am"] == (today - timedelta(days=20)).isoformat()
    assert entry["faellig_am"] == (today - timedelta(days=6)).isoformat()


def test_overdue_day_count(client, seed_book_member):
    """tage_ueberfaellig is the number of days since the due date."""

    book_id, member_id = seed_book_member
    today = date.today()

    _add_loan(
        book_id,
        member_id,
        ausgeliehen_am=today - timedelta(days=30),
        faellig_am=today - timedelta(days=16),
    )

    body = client.get("/loans/overdue").json()
    assert body["total"] == 1
    assert body["items"][0]["tage_ueberfaellig"] == 16


def test_overdue_envelope_and_offset(client, seed_book_member):
    """The page envelope honours limit/offset and keeps the full total."""

    book_id, member_id = seed_book_member
    today = date.today()

    for days in (9, 7, 5):
        _add_loan(
            book_id,
            member_id,
            ausgeliehen_am=today - timedelta(days=days + 14),
            faellig_am=today - timedelta(days=days),
        )

    first = client.get("/loans/overdue", params={"limit": 2, "offset": 0}).json()
    assert first["total"] == 3
    assert first["limit"] == 2
    assert first["offset"] == 0
    assert [item["tage_ueberfaellig"] for item in first["items"]] == [9, 7]

    second = client.get("/loans/overdue", params={"limit": 2, "offset": 2}).json()
    assert second["total"] == 3
    assert second["limit"] == 2
    assert second["offset"] == 2
    assert [item["tage_ueberfaellig"] for item in second["items"]] == [5]


def test_overdue_empty(client):
    """A request with nothing overdue returns an empty page, not an error."""

    body = client.get("/loans/overdue", params={"offset": 0, "limit": 1}).json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)


def test_overdue_limit_above_max_rejected(client):
    """limit above 100 is a validation error (shared contract)."""

    response = client.get("/loans/overdue", params={"limit": 101})
    assert response.status_code == 422
