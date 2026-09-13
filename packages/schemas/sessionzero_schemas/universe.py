from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UniverseEligibilityReason(StrEnum):
    INSTRUMENT_NOT_ONLINE = "INSTRUMENT_NOT_ONLINE"
    MISSING_NATIVE_MAPPING = "MISSING_NATIVE_MAPPING"
    UNSUPPORTED_INTERVAL = "UNSUPPORTED_INTERVAL"
    MALFORMED_METADATA = "MALFORMED_METADATA"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"


class UniverseMappingStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class ManifestEntryStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_WITH_WARNINGS = "SUCCEEDED_WITH_WARNINGS"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    return value


class UniverseMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reality_symbol: str
    base_coin: str
    quote_coin: str
    native_ticker: str | None
    instrument_status: str
    is_reality: bool
    launch_time: datetime | None = None
    price_precision: int | None = Field(default=None, ge=0)
    quantity_precision: int | None = Field(default=None, ge=0)
    trading_periods: tuple[str, ...] = ()
    weekend_tradable: bool | None = None
    mapping_status: UniverseMappingStatus
    source_session_status: str
    source_session_mode: str
    technically_eligible: bool
    exclusion_reasons: tuple[UniverseEligibilityReason, ...]
    raw_metadata_key: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("launch_time")
    @classmethod
    def validate_launch_time(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_eligibility(self) -> UniverseMember:
        if self.is_reality is not True:
            raise ValueError("universe member must be explicitly identified as Reality")
        if self.technically_eligible == bool(self.exclusion_reasons):
            raise ValueError("eligibility and exclusion reasons contradict")
        if self.mapping_status == UniverseMappingStatus.AVAILABLE and not self.native_ticker:
            raise ValueError("available mapping requires native_ticker")
        return self


class RealityUniverseSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    universe_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str
    transformation_version: str
    generated_at: datetime
    source: str
    source_endpoint: str
    source_version: str
    interval: str
    members: tuple[UniverseMember, ...]
    raw_provider_payload: dict[str, Any]

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_members(self) -> RealityUniverseSnapshot:
        symbols = tuple(member.reality_symbol for member in self.members)
        if not symbols or symbols != tuple(sorted(symbols)) or len(symbols) != len(set(symbols)):
            raise ValueError("universe members must be non-empty, unique, canonical symbol order")
        return self


class HistoricalManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    native_ticker: str | None
    interval: str
    requested_start: datetime
    requested_end: datetime
    observed_start: datetime | None = None
    observed_end: datetime | None = None
    page_count: int = Field(ge=0)
    raw_records_received: int = Field(ge=0)
    normalized_records_written: int = Field(ge=0)
    records_available_for_requested_window: int = Field(ge=0)
    quality_status: str | None = None
    missing_while_expected_open: int = Field(ge=0)
    source_session_unknown: int = Field(ge=0)
    ingestion_run_id: str | None = None
    status: ManifestEntryStatus
    failure_code: str | None = None

    @field_validator("requested_start", "requested_end", "observed_start", "observed_end")
    @classmethod
    def validate_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_outcome(self) -> HistoricalManifestEntry:
        if self.requested_end <= self.requested_start:
            raise ValueError("manifest range must be increasing")
        if self.status in {
            ManifestEntryStatus.SUCCEEDED,
            ManifestEntryStatus.SUCCEEDED_WITH_WARNINGS,
        }:
            if self.ingestion_run_id is None or self.failure_code is not None:
                raise ValueError("successful outcome requires an ingestion run and no failure")
        elif self.failure_code is None:
            raise ValueError("non-success outcome requires failure_code")
        return self


class HistoricalIngestionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    universe_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    transformation_version: str
    git_commit: str
    generated_at: datetime
    entries: tuple[HistoricalManifestEntry, ...]

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        return _utc(value)
