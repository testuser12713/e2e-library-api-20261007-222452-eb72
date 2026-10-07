"""Application configuration.

Settings are read from the environment (and an optional ``.env`` file) when the
settings object is created, never at import time.  ``get_settings`` is cached so
that every part of the app sees the same validated instance.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the library API.

    ``api_key`` is optional: when it is unset every write request is rejected
    with 401.  ``database_url`` defaults to a SQLite file beside the app.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str | None = None
    database_url: str = "sqlite:///./library.db"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
