from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint("status IN ('RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_run_status"),
        CheckConstraint("records_received >= 0", name="ck_run_records_received_nonnegative"),
        CheckConstraint("records_written >= 0", name="ck_run_records_written_nonnegative"),
        CheckConstraint(
            "pages_requested IS NULL OR pages_requested >= 1",
            name="ck_run_pages_requested_positive",
        ),
        CheckConstraint(
            "quality_status IS NULL OR quality_status IN ('PASS', 'WARN', 'FAIL')",
            name="ck_run_quality_status",
        ),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(128))
    requested_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interval: Mapped[str | None] = mapped_column(String(16))
    pages_requested: Mapped[int | None] = mapped_column(Integer)
    quality_status: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RawMarketObservation(Base):
    __tablename__ = "raw_market_observations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "source",
            "symbol",
            "market",
            "endpoint",
            "event_time",
            name="uq_raw_observation_per_run",
        ),
        Index("ix_raw_market_identity", "source", "symbol", "market", "event_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.run_id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NormalizedMarketCandle(Base):
    __tablename__ = "normalized_market_candles"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "symbol",
            "market",
            "interval",
            "event_time",
            name="uq_normalized_candle_market_identity",
        ),
        CheckConstraint("high >= low", name="ck_candle_high_gte_low"),
        Index("ix_normalized_candle_lookup", "symbol", "interval", "event_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric())
    turnover: Mapped[Decimal | None] = mapped_column(Numeric())
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
