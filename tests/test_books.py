"""Tests for the books CRUD endpoints (SPEC AC-02 .. AC-05).

Each test provisions its own books with unique ISBNs so it neither collides
with nor asserts about rows another test slice may create.
"""

from datetime import date, timedelta
from itertools import count

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Book, Loan, Member

_ISBN_SEQUENCE = count(1)


@pytest.fixture(autouse=True)
def _isolate(test_engine):
    """Remove exactly the books and members a test created, leaving the rest."""

    with Session(test_engine) as session:
        books_before = set(session.scalars(select(Book.id)).all())
        members_before = set(session.scalars(select(Member.id)).all())
    yield
    with Session(test_engine) as session:
        new_books = set(session.scalars(select(Book.id)).all()) - books_before
        new_members = set(session.scalars(select(Member.id)).all()) - members_before
        if new_books:
            session.execute(delete(Loan).where(Loan.book_id.in_(new_books)))
            session.execute(delete(Book).where(Book.id.in_(new_books)))
        if new_members:
            session.execute(delete(Loan).where(Loan.member_id.in_(new_members)))
            session.execute(delete(Member).where(Member.id.in_(new_members)))
        session.commit()


def _isbn() -> str:
    """Return a valid, unique ISBN-13 for a test book."""

    return f"978{next(_ISBN_SEQUENCE):010d}"


def _create_book(client, headers, **overrides) -> dict:
    payload = {
        "titel": "Der Steppenwolf",
        "autor": "Hermann Hesse",
        "isbn": _isbn(),
        "erscheinungsjahr": 1927,
        "exemplare": 3,
    }
    payload.update(overrides)
    response = client.post("/books", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _count_rows(test_engine, isbn: str) -> int:
    with Session(test_engine) as session:
        return int(
            session.scalar(select(func.count()).select_from(Book).where(Book.isbn == isbn)) or 0
        )


def test_create_book_returns_201_with_id_and_free_copies(client, auth_headers):
    isbn = _isbn()
    response = client.post(
        "/books",
        json={
            "titel": "Stein der Weisen",
            "autor": "Joanne Rowling",
            "isbn": isbn,
            "erscheinungsjahr": 1997,
            "exemplare": 2,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["isbn"] == isbn
    assert body["exemplare"] == 2
    assert body["verfuegbar"] == 2


def test_duplicate_isbn_returns_409_and_inserts_no_second_row(client, auth_headers, test_engine):
    isbn = _isbn()
    _create_book(client, auth_headers, isbn=isbn)

    response = client.post(
        "/books",
        json={"titel": "Kopie", "autor": "Jemand", "isbn": isbn, "exemplare": 1},
        headers=auth_headers,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "duplicate_isbn"
    assert body["error"]["details"] is None
    assert _count_rows(test_engine, isbn) == 1


def test_get_book_returns_the_book(client, auth_headers):
    created = _create_book(client, auth_headers)

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["titel"] == created["titel"]
    assert body["verfuegbar"] == created["exemplare"]


def test_get_unknown_book_returns_404(client):
    response = client.get("/books/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"


def test_list_books_returns_pagination_envelope(client, auth_headers):
    created = _create_book(client, auth_headers)

    response = client.get("/books")

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"items", "total", "limit", "offset"}
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] >= 1
    ids = {item["id"] for item in body["items"]}
    assert created["id"] in ids
    assert all("verfuegbar" in item for item in body["items"])


def test_search_is_case_insensitive_in_title_or_author(client, auth_headers):
    by_title = _create_book(client, auth_headers, titel=f"Stein {_isbn()}", autor="Anonym")
    by_author = _create_book(client, auth_headers, titel="Ein anderes Buch", autor="Steinmann")
    non_match = _create_book(client, auth_headers, titel="Voellig anders", autor="Niemand")

    response = client.get("/books", params={"q": "stein"})

    assert response.status_code == 200
    matched = {item["id"] for item in response.json()["items"]}
    assert by_title["id"] in matched
    assert by_author["id"] in matched
    assert non_match["id"] not in matched


def test_search_without_hits_is_empty(client, auth_headers):
    _create_book(client, auth_headers, titel="Stein der Weisen", autor="Rowling")

    response = client.get("/books", params={"q": "zzz-no-such-term-zzz"})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_search_limit_offset_cuts_items_but_keeps_total(client, auth_headers):
    token = f"seitentest{next(_ISBN_SEQUENCE)}"
    for index in range(3):
        _create_book(client, auth_headers, titel=f"{token} Band {index}", autor="Autor")

    first_page = client.get("/books", params={"q": token, "limit": 2, "offset": 0}).json()

    assert first_page["total"] == 3
    assert len(first_page["items"]) == 2
    assert first_page["limit"] == 2
    assert first_page["offset"] == 0
    assert [item["titel"] for item in first_page["items"]] == [
        f"{token} Band 0",
        f"{token} Band 1",
    ]

    second_page = client.get("/books", params={"q": token, "limit": 2, "offset": 2}).json()

    assert second_page["total"] == 3
    assert len(second_page["items"]) == 1
    assert second_page["items"][0]["titel"] == f"{token} Band 2"


def test_put_updates_all_fields_including_isbn(client, auth_headers):
    created = _create_book(client, auth_headers)
    new_isbn = _isbn()

    response = client.put(
        f"/books/{created['id']}",
        json={
            "titel": "Neuer Titel",
            "autor": "Neue Autorin",
            "isbn": new_isbn,
            "erscheinungsjahr": 2001,
            "exemplare": 5,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["titel"] == "Neuer Titel"
    assert body["autor"] == "Neue Autorin"
    assert body["isbn"] == new_isbn
    assert body["erscheinungsjahr"] == 2001
    assert body["exemplare"] == 5
    assert body["verfuegbar"] == 5


def test_patch_updates_only_provided_fields(client, auth_headers):
    created = _create_book(client, auth_headers, titel="Alt", autor="Bleibt", exemplare=4)

    response = client.patch(
        f"/books/{created['id']}",
        json={"titel": "Neu"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["titel"] == "Neu"
    assert body["autor"] == "Bleibt"
    assert body["exemplare"] == 4


def test_update_to_duplicate_isbn_returns_409(client, auth_headers):
    first = _create_book(client, auth_headers)
    second = _create_book(client, auth_headers)

    response = client.patch(
        f"/books/{second['id']}",
        json={"isbn": first["isbn"]},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_isbn"


def test_delete_book_without_loans_returns_204(client, auth_headers):
    created = _create_book(client, auth_headers)

    response = client.delete(f"/books/{created['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_with_open_loan_returns_409(client, auth_headers, test_engine):
    created = _create_book(client, auth_headers, exemplare=2)
    today = date.today()
    with Session(test_engine) as session:
        member = Member(
            name="Leiherin",
            email=f"leiher{_isbn()}@example.com",
            mitglied_seit=today,
            offene_ausleihen=1,
        )
        session.add(member)
        session.flush()
        session.add(
            Loan(
                book_id=created["id"],
                member_id=member.id,
                ausgeliehen_am=today,
                faellig_am=today + timedelta(days=14),
                zurueckgegeben_am=None,
            )
        )
        session.commit()

    detail = client.get(f"/books/{created['id']}").json()
    assert detail["verfuegbar"] == 1

    response = client.delete(f"/books/{created['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "book_has_open_loans"
