from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
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


class RawReferenceObservation(Base):
    __tablename__ = "raw_reference_observations"
    __table_args__ = (
        UniqueConstraint("run_id", "provider_record_key", name="uq_raw_reference_response_per_run"),
        Index("ix_raw_reference_endpoint", "endpoint", "provider_request_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.run_id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    request_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provider_request_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RealitySymbolMappingRow(Base):
    __tablename__ = "reality_symbol_mappings"
    __table_args__ = (
        UniqueConstraint("source", "provider_record_key", name="uq_reality_mapping_version"),
        Index("ix_reality_mapping_lookup", "reality_symbol", "ingestion_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    reality_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    base_coin: Mapped[str] = mapped_column(String(64), nullable=False)
    native_ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    trading_periods: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    weekend_tradable: Mapped[bool] = mapped_column(nullable=False)
    effective_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permanent_identifier: Mapped[str | None] = mapped_column(String(128))
    availability_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_time_status: Mapped[str] = mapped_column(String(16), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_or_derived: Mapped[str] = mapped_column(String(16), nullable=False)


class CorporateActionRow(Base):
    __tablename__ = "corporate_actions"
    __table_args__ = (
        UniqueConstraint("source", "provider_record_key", name="uq_corporate_action_version"),
        CheckConstraint(
            "action_type IN ('CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'REVERSE_SPLIT')",
            name="ck_corporate_action_type",
        ),
        Index("ix_corporate_action_lookup", "native_ticker", "effective_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    native_ticker: Mapped[str | None] = mapped_column(String(32))
    provider_symbol: Mapped[str | None] = mapped_column(String(64))
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    ex_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    cash_amount_per_share: Mapped[Decimal | None] = mapped_column(Numeric())
    stock_amount_per_share: Mapped[Decimal | None] = mapped_column(Numeric())
    currency: Mapped[str | None] = mapped_column(String(16))
    numerator: Mapped[Decimal | None] = mapped_column(Numeric())
    denominator: Mapped[Decimal | None] = mapped_column(Numeric())
    adjustment_ratio: Mapped[Decimal | None] = mapped_column(Numeric())
    provider_status: Mapped[str | None] = mapped_column(String(32))
    event_timezone: Mapped[str | None] = mapped_column(String(32))
    trading_halt_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trading_halt_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_time_status: Mapped[str] = mapped_column(String(16), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_or_derived: Mapped[str] = mapped_column(String(16), nullable=False)


class ShareCapitalChangeRow(Base):
    __tablename__ = "share_capital_changes"
    __table_args__ = (
        UniqueConstraint("source", "provider_record_key", name="uq_share_capital_version"),
        Index("ix_share_capital_lookup", "native_ticker", "effective_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    native_ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_shares: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    common_shares: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    preferred_shares: Mapped[Decimal | None] = mapped_column(Numeric())
    other_shares: Mapped[Decimal | None] = mapped_column(Numeric())
    special_explanation: Mapped[str | None] = mapped_column(String())
    change_reason: Mapped[str | None] = mapped_column(String())
    availability_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_time_status: Mapped[str] = mapped_column(String(16), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_or_derived: Mapped[str] = mapped_column(String(16), nullable=False)


class SuspensionRecordRow(Base):
    __tablename__ = "suspension_records"
    __table_args__ = (
        UniqueConstraint("source", "provider_record_key", name="uq_suspension_version"),
        Index("ix_suspension_lookup", "native_ticker", "suspension_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    native_ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    suspension_date: Mapped[date] = mapped_column(Date, nullable=False)
    suspension_time: Mapped[str | None] = mapped_column(String(16))
    suspension_reason: Mapped[str | None] = mapped_column(String())
    suspension_price: Mapped[Decimal | None] = mapped_column(Numeric())
    resumption_date: Mapped[date | None] = mapped_column(Date)
    resumption_quote_time: Mapped[str | None] = mapped_column(String(16))
    resumption_trading_time: Mapped[str | None] = mapped_column(String(16))
    event_timezone: Mapped[str | None] = mapped_column(String(32))
    availability_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_time_status: Mapped[str] = mapped_column(String(16), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_or_derived: Mapped[str] = mapped_column(String(16), nullable=False)


class SourceSessionMetadataRow(Base):
    __tablename__ = "source_session_metadata"
    __table_args__ = (
        UniqueConstraint("source", "provider_record_key", name="uq_source_session_version"),
        Index("ix_source_session_lookup", "market", "ingestion_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    daylight_type: Mapped[str] = mapped_column(String(16), nullable=False)
    state_time_zone: Mapped[str] = mapped_column(String(32), nullable=False)
    calendar_time_zone: Mapped[str] = mapped_column(String(32), nullable=False)
    sessions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    closures: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    regular_closure_days: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    availability_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_time_status: Mapped[str] = mapped_column(String(16), nullable=False)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_or_derived: Mapped[str] = mapped_column(String(16), nullable=False)
