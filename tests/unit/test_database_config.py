from __future__ import annotations

import pytest
from pydantic import ValidationError
from sessionzero_config import Settings
from sessionzero_database import create_database_engine


def test_database_url_is_loaded_and_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSIONZERO_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/sessionzero_test")
    settings = Settings.from_env()
    assert settings.environment == "test"
    assert settings.require_database_url() == (
        "postgresql+psycopg://user:secret@localhost/sessionzero_test"
    )


@pytest.mark.parametrize(
    "url",
    ["sqlite:///:memory:", "sqlite:///database.db", "mysql://localhost/sessionzero"],
)
def test_non_postgresql_database_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValidationError, match="must use PostgreSQL"):
        Settings(database_url=url)


def test_missing_database_url_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        Settings(environment="production").require_database_url()


def test_engine_rejects_implicit_or_sqlite_storage() -> None:
    with pytest.raises(ValueError, match=r"postgresql\+psycopg"):
        create_database_engine("sqlite:///:memory:")
