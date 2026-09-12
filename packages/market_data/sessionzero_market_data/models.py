from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class SourceSessionMode(StrEnum):
    TWENTY_FOUR_FIVE = "24_5"
    TWENTY_FOUR_SEVEN = "24_7"
    REGULAR_OR_EXTENDED = "REGULAR_OR_EXTENDED"
    UNKNOWN = "UNKNOWN"


class SourceAvailabilityState(StrEnum):
    EXPECTED_OPEN = "EXPECTED_OPEN"
    EXPECTED_CLOSED = "EXPECTED_CLOSED"
    UNKNOWN = "UNKNOWN"


class SessionZeroState(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class CashSessionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    as_of: datetime
    cash_market_open: bool
    reference_session_date: date
    regular_open: datetime
    regular_close: datetime
    previous_cash_close: datetime
    next_cash_open: datetime
    local_date_is_session: bool
    local_date_is_holiday: bool
    early_close: bool


class SourceSessionCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    effective_from: datetime
    effective_to: datetime | None = None
    session_mode: SourceSessionMode
    source: str
    evidence_url: str
    verified_at: datetime
    notes: str

    @model_validator(mode="after")
    def validate_effective_range(self) -> SourceSessionCapability:
        timestamps = (self.effective_from, self.verified_at)
        if self.effective_to is not None:
            timestamps += (self.effective_to,)
            if self.effective_to <= self.effective_from:
                raise ValueError("effective_to must be later than effective_from")
        if any(value.tzinfo is None or value.utcoffset() is None for value in timestamps):
            raise ValueError("capability timestamps must be timezone-aware")
        if self.symbol != "*" and self.symbol != self.symbol.upper():
            raise ValueError("capability symbol must be uppercase or wildcard")
        return self


class SourceSessionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    as_of: datetime
    availability: SourceAvailabilityState
    session_mode: SourceSessionMode
    capability_effective_from: datetime | None = None
    evidence_url: str | None = None
    reason: str


class SessionZeroContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    as_of: datetime
    cash_market_open: bool
    session_zero_state: SessionZeroState
    previous_cash_close: datetime
    next_cash_open: datetime
    reference_session_date: date
    source_states: tuple[SourceAvailabilityState, ...]
