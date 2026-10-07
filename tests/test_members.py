"""Tests for the members CRUD slice (AC-06).

Each test creates its own data and removes exactly the rows it created, so the
suite can run alongside the other slices on the same test database.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import Loan, Member


def _member_payload(name: str, email: str, **extra) -> dict:
    payload = {"name": name, "email": email}
    payload.update(extra)
    return payload


@pytest.fixture
def member_ids(client, test_engine):
    """Track member ids created through the API and delete them afterwards."""

    created: list[int] = []
    yield created
    session = sessionmaker(bind=test_engine)()
    try:
        for member_id in created:
            member = session.get(Member, member_id)
            if member is not None:
                session.delete(member)
        session.commit()
    finally:
        session.close()


def test_create_member_returns_201_with_default_mitglied_seit(client, auth_headers, member_ids):
    response = client.post(
        "/members",
        json=_member_payload("Ada Lovelace", "ada@example.com"),
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    member_ids.append(body["id"])
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["mitglied_seit"] == date.today().isoformat()
    assert body["offene_ausleihen"] == 0


def test_create_member_accepts_explicit_mitglied_seit(client, auth_headers, member_ids):
    response = client.post(
        "/members",
        json=_member_payload("Grace Hopper", "grace@example.com", mitglied_seit="2020-01-31"),
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    member_ids.append(body["id"])
    assert body["mitglied_seit"] == "2020-01-31"


def test_duplicate_email_is_rejected_case_insensitively(
    client, auth_headers, member_ids, test_engine
):
    first = client.post(
        "/members",
        json=_member_payload("Alan Turing", "alan@example.com"),
        headers=auth_headers,
    )
    assert first.status_code == 201
    member_ids.append(first.json()["id"])

    second = client.post(
        "/members",
        json=_member_payload("Someone Else", "ALAN@Example.com"),
        headers=auth_headers,
    )
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "duplicate_email"
    assert "details" in body["error"]

    session = sessionmaker(bind=test_engine)()
    try:
        matches = session.scalars(
            select(Member).where(Member.email.ilike("alan@example.com"))
        ).all()
    finally:
        session.close()
    assert len(matches) == 1


def test_invalid_email_is_rejected_with_field_detail(client, auth_headers):
    response = client.post(
        "/members",
        json=_member_payload("Bad Email", "not-an-email"),
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert "email" in fields


def test_missing_name_is_rejected_with_field_detail(client, auth_headers):
    response = client.post(
        "/members",
        json={"email": "no-name@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert "name" in fields


def test_create_requires_api_key(client):
    response = client.post(
        "/members",
        json=_member_payload("No Key", "no-key@example.com"),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_unknown_member_returns_404(client):
    response = client.get("/members/999999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_member_returns_the_member(client, auth_headers, member_ids):
    created = client.post(
        "/members",
        json=_member_payload("Katherine Johnson", "katherine@example.com"),
        headers=auth_headers,
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    member_ids.append(member_id)

    response = client.get(f"/members/{member_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "katherine@example.com"


def test_list_members_returns_page_envelope_sorted_by_name_then_id(
    client, auth_headers, member_ids
):
    names = ["Zeta Member", "Alpha Member", "Mu Member"]
    ids = []
    for index, name in enumerate(names):
        created = client.post(
            "/members",
            json=_member_payload(name, f"sort-{index}@example.com"),
            headers=auth_headers,
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])
    member_ids.extend(ids)

    response = client.get("/members", params={"limit": 100, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["limit"] == 100
    assert body["offset"] == 0
    assert body["total"] >= len(names)

    listed = [(item["name"], item["id"]) for item in body["items"]]
    assert listed == sorted(listed)


def test_offene_ausleihen_counts_only_open_loans(client, auth_headers, member_ids, test_engine):
    created = client.post(
        "/members",
        json=_member_payload("Loan Counter", "loans@example.com"),
        headers=auth_headers,
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    member_ids.append(member_id)

    session = sessionmaker(bind=test_engine)()
    loan_ids: list[int] = []
    try:
        today = date.today()
        open_loan = Loan(
            book_id=987654,
            member_id=member_id,
            ausgeliehen_am=today,
            faellig_am=today + timedelta(days=14),
            zurueckgegeben_am=None,
        )
        returned_loan = Loan(
            book_id=987654,
            member_id=member_id,
            ausgeliehen_am=today - timedelta(days=20),
            faellig_am=today - timedelta(days=6),
            zurueckgegeben_am=today - timedelta(days=1),
        )
        session.add_all([open_loan, returned_loan])
        session.commit()
        session.refresh(open_loan)
        session.refresh(returned_loan)
        loan_ids.extend([open_loan.id, returned_loan.id])
    finally:
        session.close()

    try:
        response = client.get(f"/members/{member_id}")
        assert response.status_code == 200
        assert response.json()["offene_ausleihen"] == 1
    finally:
        session = sessionmaker(bind=test_engine)()
        try:
            for loan_id in loan_ids:
                loan = session.get(Loan, loan_id)
                if loan is not None:
                    session.delete(loan)
            session.commit()
        finally:
            session.close()


def test_put_updates_name_email_and_mitglied_seit(client, auth_headers, member_ids):
    created = client.post(
        "/members",
        json=_member_payload("Old Name", "old@example.com"),
        headers=auth_headers,
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    member_ids.append(member_id)

    response = client.put(
        f"/members/{member_id}",
        json={"name": "New Name", "email": "new@example.com", "mitglied_seit": "2021-06-15"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["email"] == "new@example.com"
    assert body["mitglied_seit"] == "2021-06-15"


def test_patch_updates_one_field(client, auth_headers, member_ids):
    created = client.post(
        "/members",
        json=_member_payload("Patch Me", "patch-me@example.com"),
        headers=auth_headers,
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    member_ids.append(member_id)

    response = client.patch(
        f"/members/{member_id}",
        json={"name": "Patched"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Patched"
    assert body["email"] == "patch-me@example.com"


def test_update_with_duplicate_email_returns_409(client, auth_headers, member_ids):
    first = client.post(
        "/members",
        json=_member_payload("First", "first-dup@example.com"),
        headers=auth_headers,
    )
    second = client.post(
        "/members",
        json=_member_payload("Second", "second-dup@example.com"),
        headers=auth_headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    member_ids.extend([first.json()["id"], second.json()["id"]])

    response = client.patch(
        f"/members/{second.json()['id']}",
        json={"email": "FIRST-DUP@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"


def test_update_unknown_member_returns_404(client, auth_headers):
    response = client.patch(
        "/members/999999999",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_member_then_second_delete_returns_404(client, auth_headers):
    created = client.post(
        "/members",
        json=_member_payload("Delete Me", "delete-me@example.com"),
        headers=auth_headers,
    )
    assert created.status_code == 201
    member_id = created.json()["id"]

    first = client.delete(f"/members/{member_id}", headers=auth_headers)
    assert first.status_code == 204
    assert first.content == b""

    second = client.delete(f"/members/{member_id}", headers=auth_headers)
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "not_found"
