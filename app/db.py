"""Database engine, session factory and declarative base.

The engine is built from ``settings.database_url`` (SQLite by default).  WAL
journal mode is enabled on every connection so that concurrent reads do not
block the writer.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_wal(dbapi_connection, _connection_record) -> None:
    """Switch each new SQLite connection to WAL journal mode."""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    """Yield a database session and always close it afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
