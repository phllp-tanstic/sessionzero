"""Provider-neutral native observations. No public API or research feature integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sessionzero_schemas import EvidenceQualifiedCohort

from .interfaces import TradingCalendarProvider


class NativeCapability(StrEnum):
    AVAILABLE = "AVAILABLE"
    GATED = "GATED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class NativeDataError(RuntimeError):
    """Safe, static error codes only; never wrap provider text or request headers."""

    def __init__(
        self,
        code: str,
        state: NativeCapability = NativeCapability.UNAVAILABLE,
        *,
        details: dict[str, str] | None = None,
    ):
        self.code = code
        self.details = details or {}
        self.state = state
        super().__init__(code)


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(UTC)


class NativeInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reality_symbol: str
    native_ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,31}$")
    universe_version: str
    cohort_version: str
    mapping_source: Literal["bitget"] = "bitget"


def mapped_instruments(cohort: EvidenceQualifiedCohort) -> tuple[NativeInstrument, ...]:
    return tuple(
        NativeInstrument(
            reality_symbol=m.symbol,
            native_ticker=m.native_ticker,
            universe_version=cohort.universe_version,
            cohort_version=cohort.cohort_version,
        )
        for m in cohort.members
    )


class NativeCandle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str
    native_ticker: str
    interval: Literal["1Min"] = "1Min"
    feed: str
    adjustment: Literal["raw"] = "raw"
    event_time: datetime
    ingestion_time: datetime
    session_date: date  # New York date; does not assert regular-session membership
    open: Decimal = Field(gt=0, allow_inf_nan=False)
    high: Decimal = Field(gt=0, allow_inf_nan=False)
    low: Decimal = Field(gt=0, allow_inf_nan=False)
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    volume: Decimal = Field(ge=0, allow_inf_nan=False)
    trade_count: int = Field(ge=0, strict=True)
    vwap: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    page_index: int = Field(ge=0)

    @field_validator("event_time", "ingestion_time")
    @classmethod
    def timestamps(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def prices(self) -> NativeCandle:
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("impossible OHLC")
        if self.event_time.second or self.event_time.microsecond:
            raise ValueError("unaligned minute timestamp")
        return self


@dataclass(frozen=True)
class NativePage:
    endpoint: str
    params: dict[str, str | int]
    ingestion_time: datetime
    response_headers: dict[str, str]  # allowlist only, never authentication
    body: str  # exact decoded JSON text preserves provider decimal lexemes


@dataclass(frozen=True)
class NativeHistory:
    instrument: NativeInstrument
    start: datetime
    end: datetime
    pages: tuple[NativePage, ...]
    candles: tuple[NativeCandle, ...]
    source: str
    clipped_count: int = 0


@dataclass(frozen=True)
class NativeTarget:
    instrument: NativeInstrument
    session_date: date
    regular_open: datetime
    regular_close: datetime
    definition: str
    status: str
    candle: NativeCandle | None
    price: Decimal | None
    history: NativeHistory


class NativeEquityProvider(Protocol):
    def get_instrument(self, reality_symbol: str) -> NativeInstrument: ...
    def get_candles(self, reality_symbol: str, start: datetime, end: datetime) -> NativeHistory: ...
    def get_session_open(self, reality_symbol: str, session_date: date) -> NativeTarget: ...
    def get_session_close(self, reality_symbol: str, session_date: date) -> NativeTarget: ...
    def health(self) -> NativeCapability: ...


def session_target(
    provider: NativeEquityProvider,
    calendar: TradingCalendarProvider,
    symbol: str,
    session_date: date,
    *,
    opening: bool,
) -> NativeTarget:
    session = calendar.session_on(session_date)
    expected = session.regular_open if opening else session.regular_close - timedelta(minutes=1)
    history = provider.get_candles(symbol, expected, expected + timedelta(minutes=1))
    for candle in history.candles:
        if candle.event_time != expected or not (
            session.regular_open <= candle.event_time < session.regular_close
        ):
            raise NativeDataError("SESSION_BOUNDARY_LEAKAGE")
    if len(history.candles) > 1:
        raise NativeDataError("DUPLICATE_TARGET")
    candle = history.candles[0] if history.candles else None
    return NativeTarget(
        history.instrument,
        session_date,
        session.regular_open,
        session.regular_close,
        "FIRST_1M_BAR_OPEN" if opening else "LAST_1M_BAR_CLOSE",
        "AVAILABLE" if candle else "MISSING_BOUNDARY_MINUTE",
        candle,
        (candle.open if opening else candle.close) if candle else None,
        history,
    )
