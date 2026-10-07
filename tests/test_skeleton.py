"""Skeleton tests: health, contract routing, auth gating and persistence.

These tests assert what the scaffold itself delivers — never the temporary
answer of a stub body owned by another ticket.
"""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Book

CONTRACT_PATHS = {
    "/health",
    "/books",
    "/books/{book_id}",
    "/members",
    "/members/{member_id}",
    "/loans",
    "/loans/{loan_id}/return",
    "/loans/overdue",
}


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_are_served(client):
    assert client.get("/docs").status_code == 200


def test_openapi_contains_every_contract_path(client):
    paths = client.get("/openapi.json").json()["paths"]
    missing = CONTRACT_PATHS - set(paths)
    assert not missing, f"missing contract paths: {sorted(missing)}"


def test_contract_methods_are_registered(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths["/books"]) >= {"get", "post"}
    assert set(paths["/books/{book_id}"]) >= {"get", "put", "patch", "delete"}
    assert set(paths["/members"]) >= {"get", "post"}
    assert set(paths["/members/{member_id}"]) >= {"get", "put", "patch", "delete"}
    assert "post" in paths["/loans"]
    assert "post" in paths["/loans/{loan_id}/return"]
    assert "get" in paths["/loans/overdue"]


def test_write_route_rejects_missing_api_key(client):
    response = client.post(
        "/books",
        json={"titel": "T", "autor": "A", "isbn": "978-3-16-148410-0", "exemplare": 1},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert "details" in body["error"]


def test_write_route_rejects_wrong_api_key(client):
    response = client.post(
        "/books",
        json={"titel": "T", "autor": "A", "isbn": "978-3-16-148410-0", "exemplare": 1},
        headers={"X-API-Key": "definitely-wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_wrong_api_key_does_not_change_data(client, test_engine):
    response = client.post(
        "/books",
        json={"titel": "No", "autor": "No", "isbn": "978-3-16-148410-0"},
        headers={"X-API-Key": "nope"},
    )
    assert response.status_code == 401
    session = sessionmaker(bind=test_engine)()
    try:
        assert session.scalars(select(Book)).all() == []
    finally:
        session.close()


def test_invalid_body_uses_unified_validation_error(client, auth_headers):
    response = client.post(
        "/books",
        json={"autor": "Ohne Titel"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert "titel" in fields


def test_read_route_is_not_gated(client):
    response = client.get("/books")
    assert response.status_code != 404
    assert response.status_code not in (401, 403)


def test_row_survives_a_fresh_engine_on_the_same_file(tmp_path):
    db_file = tmp_path / "persist.db"
    url = f"sqlite:///{db_file}"

    first_engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=first_engine)
    first_session = sessionmaker(bind=first_engine)
    with first_session() as session:
        session.add(
            Book(
                titel="Der Steppenwolf",
                autor="Hermann Hesse",
                isbn="978-3-16-148410-0",
                exemplare=1,
                verfuegbar=1,
            )
        )
        session.commit()
    first_engine.dispose()

    second_engine = create_engine(url, connect_args={"check_same_thread": False})
    second_session = sessionmaker(bind=second_engine)
    with second_session() as session:
        books = session.scalars(select(Book)).all()
    second_engine.dispose()

    assert [book.titel for book in books] == ["Der Steppenwolf"]
