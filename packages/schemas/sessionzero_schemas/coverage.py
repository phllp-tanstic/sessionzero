from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CoverageStatus(StrEnum):
    SUFFICIENT_MINIMUM_HISTORY = "SUFFICIENT_MINIMUM_HISTORY"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    SOURCE_SESSION_TOO_UNKNOWN = "SOURCE_SESSION_TOO_UNKNOWN"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
    HISTORY_UNAVAILABLE = "HISTORY_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    return value


class HistoricalCoverageMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    native_ticker: str
    interval: str
    transformation_version: str
    evaluation_start: datetime
    evaluation_end: datetime
    earliest_observed_event_time: datetime | None = None
    latest_observed_event_time: datetime | None = None
    observed_duration_days: float = Field(ge=0)
    observed_record_count: int = Field(ge=0)
    expected_intervals_where_session_known: int = Field(ge=0)
    missing_while_expected_open: int = Field(ge=0)
    source_session_unknown_count: int = Field(ge=0)
    quality_status: str | None = None
    coverage_status: CoverageStatus
    minimum_total_history_days: int = Field(default=60, ge=1)
    minimum_oos_days: int = Field(default=30, ge=1)
    request_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    rate_limit_count: int = Field(default=0, ge=0)
    failure_code: str | None = None
    verification_time: datetime
    universe_version: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "evaluation_start",
        "evaluation_end",
        "earliest_observed_event_time",
        "latest_observed_event_time",
        "verification_time",
    )
    @classmethod
    def validate_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_evidence(self) -> HistoricalCoverageMember:
        if self.evaluation_end <= self.evaluation_start:
            raise ValueError("coverage evaluation range must be increasing")
        observed_times = (
            self.earliest_observed_event_time,
            self.latest_observed_event_time,
        )
        if self.observed_record_count == 0 and any(value is not None for value in observed_times):
            raise ValueError("empty coverage cannot have observed bounds")
        if self.observed_record_count > 0 and any(value is None for value in observed_times):
            raise ValueError("non-empty coverage requires observed bounds")
        if (
            self.earliest_observed_event_time is not None
            and self.latest_observed_event_time is not None
            and self.latest_observed_event_time < self.earliest_observed_event_time
        ):
            raise ValueError("observed coverage bounds are reversed")
        return self


class HistoricalCoverageProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    universe_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    interval: str
    transformation_version: str
    evaluation_start: datetime
    evaluation_end: datetime
    generated_at: datetime
    minimum_total_history_days: int = Field(default=60, ge=1)
    minimum_oos_days: int = Field(default=30, ge=1)
    members: tuple[HistoricalCoverageMember, ...]

    @field_validator("evaluation_start", "evaluation_end", "generated_at")
    @classmethod
    def validate_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_members(self) -> HistoricalCoverageProfile:
        symbols = tuple(member.symbol for member in self.members)
        if not symbols or symbols != tuple(sorted(symbols)) or len(symbols) != len(set(symbols)):
            raise ValueError("coverage members must be non-empty, unique, canonical symbol order")
        if any(member.universe_version != self.universe_version for member in self.members):
            raise ValueError("coverage members must link to the profile universe")
        if any(member.interval != self.interval for member in self.members):
            raise ValueError("coverage members must use the profile interval")
        return self
