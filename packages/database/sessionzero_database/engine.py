from __future__ import annotations

from sqlalchemy import Engine, create_engine, text


def create_database_engine(database_url: str) -> Engine:
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("database engine requires a postgresql+psycopg DATABASE_URL")
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=UTC"},
    )


def verify_database_connection(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
