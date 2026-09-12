from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawOrDerived(StrEnum):
    RAW = "RAW"
    DERIVED = "DERIVED"


class CapabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    GATED = "GATED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ProvenanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = "bitget_uta_v3"
    market: str
    ingestion_time: datetime
    raw_or_derived: RawOrDerived = RawOrDerived.RAW

    @field_validator("ingestion_time")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("timestamp must be UTC")
        return value


class MarketInstrument(ProvenanceModel):
    symbol: str
    base_coin: str
    quote_coin: str
    status: str
    is_reality: bool
    launch_time: datetime | None = None
    price_precision: int | None = Field(default=None, ge=0)
    quantity_precision: int | None = Field(default=None, ge=0)

    @field_validator("launch_time")
    @classmethod
    def require_launch_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("launch_time must be timezone-aware")
        if value is not None and value.utcoffset().total_seconds() != 0:
            raise ValueError("launch_time must be UTC")
        return value


class MarketTicker(ProvenanceModel):
    symbol: str
    event_time: datetime
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    volume_24h: Decimal | None = None
    turnover_24h: Decimal | None = None
    platform_turnover_24h: Decimal | None = None

    @field_validator("event_time")
    @classmethod
    def require_event_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_time must be timezone-aware")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("event_time must be UTC")
        return value


class MarketCandle(ProvenanceModel):
    symbol: str
    event_time: datetime
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    turnover: Decimal | None = None

    @field_validator("event_time")
    @classmethod
    def require_candle_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_time must be timezone-aware")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("event_time must be UTC")
        return value


class ProviderCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: str
    status: CapabilityStatus
    reason: str
    documented_endpoint: str
    observed_at: datetime | None = None
