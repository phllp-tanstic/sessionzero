from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    environment: Literal["development", "test", "production"] = "development"
    bitget_base_url: HttpUrl = HttpUrl("https://api.bitget.com")
    bitget_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    bitget_max_retries: int = Field(default=2, ge=0, le=5)
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    )
    database_url: str | None = None

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_in_production(
        cls, origins: tuple[str, ...], info: object
    ) -> tuple[str, ...]:
        if "*" in origins:
            raise ValueError("wildcard CORS origins are prohibited")
        return origins

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg driver")
        return value

    def require_database_url(self) -> str:
        if self.database_url is None:
            raise ValueError("DATABASE_URL is required for database operations")
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @classmethod
    def from_env(cls) -> Settings:
        origins = tuple(
            value.strip()
            for value in os.getenv(
                "SESSIONZERO_CORS_ORIGINS",
                "http://127.0.0.1:3000,http://localhost:3000",
            ).split(",")
            if value.strip()
        )
        return cls(
            environment=os.getenv("SESSIONZERO_ENV", "development"),
            bitget_base_url=os.getenv("BITGET_BASE_URL", "https://api.bitget.com"),
            bitget_timeout_seconds=os.getenv("BITGET_HTTP_TIMEOUT_SECONDS", "10"),
            bitget_max_retries=os.getenv("BITGET_HTTP_MAX_RETRIES", "2"),
            cors_origins=origins,
            database_url=os.getenv("DATABASE_URL"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
