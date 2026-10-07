"""FastAPI application entry point for the library API.

Run it with::

    python -m uvicorn app.main:app --port 8000
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.db import Base, engine
from app.errors import register_exception_handlers
from app.routers import books, loans, loans_overdue, members


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Validate configuration and create the schema before serving."""

    get_settings()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Stadtbibliothek API", version="1.0.0", lifespan=lifespan)

register_exception_handlers(app)

app.include_router(books.router)
app.include_router(members.router)
app.include_router(loans.router)
app.include_router(loans_overdue.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness check that also proves the configured database is reachable."""

    get_settings()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
