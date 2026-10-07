"""Shared pytest fixtures for the library API test suite.

The test database lives in a temporary directory and is wired in *before* the
application modules are imported, so the suite never touches the production
``library.db``.
"""

import os
import tempfile

_TEST_DB_DIR = tempfile.mkdtemp(prefix="library-test-db-")
TEST_API_KEY = "test-api-key"

os.environ["API_KEY"] = TEST_API_KEY
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402


def _override_get_db():
    """Yield a session bound to the test engine."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session")
def test_engine():
    """Return the test engine, with the schema created."""

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session")
def client(test_engine):
    """A TestClient running the app's lifespan against the test database."""

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers carrying the valid test API key."""

    return {"X-API-Key": TEST_API_KEY}
