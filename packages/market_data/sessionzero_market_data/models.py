from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSessionMode(StrEnum):
    TWENTY_FOUR_FIVE = "24_5"
    TWENTY_FOUR_SEVEN = "24_7"
    REGULAR_OR_EXTENDED = "REGULAR_OR_EXTENDED"
    UNKNOWN = "UNKNOWN"


class SourceAvailabilityState(StrEnum):
    EXPECTED_OPEN = "EXPECTED_OPEN"
    EXPECTED_CLOSED = "EXPECTED_CLOSED"
    UNKNOWN = "UNKNOWN"


class SourceSessionEvidenceType(StrEnum):
    SYMBOL_BATCH_CHANGE = "SYMBOL_BATCH_CHANGE"
    DATED_ENUMERATED_STATUS = "DATED_ENUMERATED_STATUS"
    GENERAL_PRODUCT_RULE = "GENERAL_PRODUCT_RULE"
    CURRENT_METADATA = "CURRENT_METADATA"
    AMBIGUOUS_NOTICE = "AMBIGUOUS_NOTICE"


class SourceSessionEvidenceConfidence(StrEnum):
    VERIFIED_EXPLICIT = "VERIFIED_EXPLICIT"
    VERIFIED_GENERAL = "VERIFIED_GENERAL"
    AMBIGUOUS_SCOPE = "AMBIGUOUS_SCOPE"


class SourceSessionCapabilityKind(StrEnum):
    TRADING_SCHEDULE = "TRADING_SCHEDULE"
    SUSPENSION = "SUSPENSION"


class SourceSessionResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    NO_EVIDENCE = "NO_EVIDENCE"
    CONFLICT = "CONFLICT"


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


class SourceSessionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(pattern=r"^[a-z0-9_.-]+$")
    provider: str
    symbols: tuple[str, ...]
    capability: SourceSessionCapabilityKind
    session_mode: SourceSessionMode
    effective_from: datetime
    effective_to: datetime | None = None
    publication_time: datetime | None = None
    evidence_url: str
    evidence_type: SourceSessionEvidenceType
    confidence: SourceSessionEvidenceConfidence
    retrieved_at: datetime
    notes: str

    @model_validator(mode="after")
    def validate_evidence(self) -> SourceSessionEvidence:
        timestamps = [self.effective_from, self.retrieved_at]
        if self.effective_to is not None:
            timestamps.append(self.effective_to)
            if self.effective_to <= self.effective_from:
                raise ValueError("effective_to must be later than effective_from")
        if self.publication_time is not None:
            timestamps.append(self.publication_time)
        if any(value.tzinfo is None or value.utcoffset() is None for value in timestamps):
            raise ValueError("evidence timestamps must be timezone-aware")
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError("evidence symbols must be unique")
        if "*" in self.symbols and self.symbols != ("*",):
            raise ValueError("wildcard evidence cannot mix with explicit symbols")
        if self.capability == SourceSessionCapabilityKind.SUSPENSION and "*" in self.symbols:
            raise ValueError("suspension evidence must enumerate affected symbols")
        if any(symbol != "*" and symbol != symbol.upper() for symbol in self.symbols):
            raise ValueError("evidence symbols must be uppercase Reality symbols")
        if not self.symbols and self.confidence != SourceSessionEvidenceConfidence.AMBIGUOUS_SCOPE:
            raise ValueError("only ambiguous-scope evidence may omit symbols")
        if (self.evidence_type == SourceSessionEvidenceType.AMBIGUOUS_NOTICE) != (
            self.confidence == SourceSessionEvidenceConfidence.AMBIGUOUS_SCOPE
        ):
            raise ValueError("ambiguous notices and ambiguous-scope confidence must agree")
        if (
            self.evidence_type == SourceSessionEvidenceType.CURRENT_METADATA
            and self.publication_time is not None
        ):
            raise ValueError("current metadata must not claim a historical publication time")
        return self


class SourceSessionEvidenceDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2]
    transformation_version: str
    retrieved_at: datetime
    evidence: tuple[SourceSessionEvidence, ...]

    @model_validator(mode="after")
    def validate_dataset(self) -> SourceSessionEvidenceDataset:
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("dataset retrieved_at must be timezone-aware")
        ids = tuple(item.evidence_id for item in self.evidence)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("evidence ids must be non-empty and unique")
        if any(item.retrieved_at != self.retrieved_at for item in self.evidence):
            raise ValueError("evidence retrieval times must match the dataset")
        return self


class SourceSessionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    as_of: datetime
    availability: SourceAvailabilityState
    session_mode: SourceSessionMode
    capability_effective_from: datetime | None = None
    evidence_url: str | None = None
    evidence_ids: tuple[str, ...] = ()
    evidence_urls: tuple[str, ...] = ()
    transformation_version: str | None = None
    resolution_status: SourceSessionResolutionStatus = SourceSessionResolutionStatus.NO_EVIDENCE
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
