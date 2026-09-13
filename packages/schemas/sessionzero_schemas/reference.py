from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .market import RawOrDerived


class ReferenceActionType(StrEnum):
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"


class PointInTimeAvailability(StrEnum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"


class ReferenceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = "bitget_uta_v3"
    endpoint: str
    source_version: str = "uta_v3"
    provider_record_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    ingestion_time: datetime
    raw_or_derived: RawOrDerived = RawOrDerived.RAW
    availability_time: datetime | None = None
    availability_time_status: PointInTimeAvailability = PointInTimeAvailability.UNKNOWN

    @field_validator("ingestion_time", "availability_time")
    @classmethod
    def require_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("timestamp must be UTC")
        return value

    @model_validator(mode="after")
    def validate_availability(self) -> ReferenceProvenance:
        if self.availability_time_status == PointInTimeAvailability.KNOWN:
            if self.availability_time is None:
                raise ValueError("known availability requires availability_time")
        elif self.availability_time is not None:
            raise ValueError("unknown availability cannot carry availability_time")
        return self


class RealitySymbolMapping(ReferenceProvenance):
    reality_symbol: str
    base_coin: str
    native_ticker: str
    name: str | None = None
    trading_periods: tuple[str, ...]
    weekend_tradable: bool
    effective_time: datetime | None = None
    permanent_identifier: str | None = None

    @field_validator("reality_symbol", "native_ticker")
    @classmethod
    def require_uppercase_identifier(cls, value: str) -> str:
        if not value or value != value.upper() or any(character.isspace() for character in value):
            raise ValueError("identifier must be non-empty uppercase text without whitespace")
        return value

    @field_validator("base_coin")
    @classmethod
    def require_provider_base_coin(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("base_coin must be non-empty text without whitespace")
        return value

    @field_validator("trading_periods")
    @classmethod
    def validate_trading_periods(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {"pre_market", "regular", "after_hours", "overnight"}
        if not value or len(value) != len(set(value)) or not set(value) <= allowed:
            raise ValueError("invalid or duplicate trading period")
        return value

    @field_validator("effective_time")
    @classmethod
    def require_effective_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None
            or value.utcoffset() is None
            or value.utcoffset().total_seconds() != 0
        ):
            raise ValueError("effective_time must be UTC")
        return value


class DividendRecord(ReferenceProvenance):
    native_ticker: str
    action_type: ReferenceActionType
    announcement_date: date | None = None
    record_date: date | None = None
    ex_date: date | None = None
    payment_date: date | None = None
    effective_date: date | None = None
    cash_amount_per_share: Decimal | None = Field(default=None, gt=0)
    stock_amount_per_share: Decimal | None = Field(default=None, gt=0)
    currency: str | None = None

    @model_validator(mode="after")
    def validate_dividend_type(self) -> DividendRecord:
        if self.action_type == ReferenceActionType.CASH_DIVIDEND:
            if self.cash_amount_per_share is None or self.stock_amount_per_share is not None:
                raise ValueError("cash dividend requires only cash_amount_per_share")
        elif self.action_type == ReferenceActionType.STOCK_DIVIDEND:
            if self.stock_amount_per_share is None or self.cash_amount_per_share is not None:
                raise ValueError("stock dividend requires only stock_amount_per_share")
        else:
            raise ValueError("DividendRecord requires a dividend action type")
        return self


class SplitRecord(ReferenceProvenance):
    native_ticker: str | None = None
    provider_symbol: str | None = None
    action_type: ReferenceActionType
    announcement_date: date | None = None
    record_date: date | None = None
    ex_date: date | None = None
    effective_date: date
    numerator: Decimal | None = Field(default=None, gt=0)
    denominator: Decimal | None = Field(default=None, gt=0)
    adjustment_ratio: Decimal | None = Field(default=None, gt=0)
    provider_status: str | None = None
    event_timezone: str | None = None
    trading_halt_start: datetime | None = None
    trading_halt_end: datetime | None = None

    @model_validator(mode="after")
    def validate_split(self) -> SplitRecord:
        if self.action_type not in {
            ReferenceActionType.SPLIT,
            ReferenceActionType.REVERSE_SPLIT,
        }:
            raise ValueError("SplitRecord requires a split action type")
        if self.native_ticker is None and self.provider_symbol is None:
            raise ValueError("split requires a native ticker or provider symbol")
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("split numerator and denominator must be supplied together")
        if self.numerator is None and self.adjustment_ratio is None:
            raise ValueError("split requires provider ratio evidence")
        for value in (self.trading_halt_start, self.trading_halt_end):
            if value is not None and (
                value.tzinfo is None
                or value.utcoffset() is None
                or value.utcoffset().total_seconds() != 0
            ):
                raise ValueError("halt timestamps must be UTC")
        if (
            self.trading_halt_start is not None
            and self.trading_halt_end is not None
            and self.trading_halt_end < self.trading_halt_start
        ):
            raise ValueError("trading halt end precedes start")
        return self


class ShareCapitalChange(ReferenceProvenance):
    native_ticker: str
    announcement_date: date | None = None
    effective_date: date
    total_shares: Decimal = Field(ge=0)
    common_shares: Decimal = Field(ge=0)
    preferred_shares: Decimal | None = Field(default=None, ge=0)
    other_shares: Decimal | None = Field(default=None, ge=0)
    special_explanation: str | None = None
    change_reason: str | None = None


class SuspensionRecord(ReferenceProvenance):
    native_ticker: str
    name: str | None = None
    suspension_date: date
    suspension_time: time | None = None
    suspension_reason: str | None = None
    suspension_price: Decimal | None = Field(default=None, gt=0)
    resumption_date: date | None = None
    resumption_quote_time: time | None = None
    resumption_trading_time: time | None = None
    event_timezone: str | None = None

    @model_validator(mode="after")
    def validate_order(self) -> SuspensionRecord:
        if self.resumption_date is not None and self.resumption_date < self.suspension_date:
            raise ValueError("resumption date precedes suspension date")
        if self.resumption_date is None and (
            self.resumption_quote_time is not None or self.resumption_trading_time is not None
        ):
            raise ValueError("resumption times require a resumption date")
        return self


class MarketSessionWindow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: str
    time_zone: str
    start_time: time
    end_time: time

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        if value not in {"pre_market", "regular", "after_hours", "overnight"}:
            raise ValueError("invalid market session state")
        return value


class MarketClosure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    remark: str | None = None
    start_local: datetime
    end_local: datetime

    @model_validator(mode="after")
    def validate_order(self) -> MarketClosure:
        if self.start_local.tzinfo is not None or self.end_local.tzinfo is not None:
            raise ValueError("provider-local closure times must remain timezone-naive")
        if self.end_local <= self.start_local:
            raise ValueError("closure end must follow start")
        return self


class SourceSessionMetadata(ReferenceProvenance):
    market: str
    daylight_type: str
    state_time_zone: str
    calendar_time_zone: str
    sessions: tuple[MarketSessionWindow, ...]
    closures: tuple[MarketClosure, ...]
    regular_closure_days: tuple[str, ...]

    @field_validator("daylight_type")
    @classmethod
    def validate_daylight_type(cls, value: str) -> str:
        if value not in {"standard", "dst"}:
            raise ValueError("invalid daylight type")
        return value

    @field_validator("regular_closure_days")
    @classmethod
    def validate_closure_days(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {
            "MONDAY",
            "TUESDAY",
            "WEDNESDAY",
            "THURSDAY",
            "FRIDAY",
            "SATURDAY",
            "SUNDAY",
        }
        if len(value) != len(set(value)) or not set(value) <= allowed:
            raise ValueError("invalid or duplicate regular closure day")
        return value
