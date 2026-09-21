"""Point-in-time capture contracts for prospective research evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CAPTURE_TRANSFORMATION_VERSION = "point_in_time_capture.v1"
SNAPSHOT_TRANSFORMATION_VERSION = "decision_snapshot.v1"
OUTCOME_TRANSFORMATION_VERSION = "prospective_outcome.v1"


class RevisionIntegrityStatus(StrEnum):
    POINT_IN_TIME_VERIFIED = "POINT_IN_TIME_VERIFIED"
    REVISION_POSSIBLE = "REVISION_POSSIBLE"
    REVISION_POLICY_UNKNOWN = "REVISION_POLICY_UNKNOWN"
    RETROSPECTIVE_ONLY = "RETROSPECTIVE_ONLY"
    PROSPECTIVELY_SAFE = "PROSPECTIVELY_SAFE"


class WorkerRunStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    MISSED_DECISION_WINDOW = "MISSED_DECISION_WINDOW"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    SKIPPED_NO_ACTION = "SKIPPED_NO_ACTION"


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


class ProspectiveRetrieval(BaseModel):
    """One immutable provider response and its normalized observation version."""

    model_config = ConfigDict(frozen=True)

    source: Literal["bitget", "alpaca"]
    symbol: str
    endpoint: str
    field_name: Literal["REALITY_DECISION_MARK", "PREVIOUS_NATIVE_CLOSE"]
    role: Literal["FEATURE"] = "FEATURE"
    event_time: datetime
    request_time: datetime
    ingestion_time: datetime
    provider_identifiers: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any]
    canonical_value: dict[str, Any]
    collector_version: str = CAPTURE_TRANSFORMATION_VERSION
    git_commit: str

    @field_validator("event_time", "request_time", "ingestion_time")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return _utc(value, "capture timestamp")

    @model_validator(mode="after")
    def validate_time_and_identity(self) -> ProspectiveRetrieval:
        event = _utc(self.event_time, "event_time")
        requested = _utc(self.request_time, "request_time")
        ingested = _utc(self.ingestion_time, "ingestion_time")
        if ingested < requested:
            raise ValueError("ingestion_time cannot precede request_time")
        if event > ingested:
            raise ValueError("future event cannot be captured")
        if not self.symbol or not self.endpoint or len(self.git_commit) < 7:
            raise ValueError("source identity is incomplete")
        return self

    @property
    def logical_key_hash(self) -> str:
        return canonical_digest(
            {
                "source": self.source,
                "symbol": self.symbol,
                "endpoint": self.endpoint,
                "field_name": self.field_name,
                "event_time": self.event_time.astimezone(UTC).isoformat(),
                "collector_version": self.collector_version,
            }
        )

    @property
    def canonical_hash(self) -> str:
        return canonical_digest(self.canonical_value)

    @property
    def version_hash(self) -> str:
        return canonical_digest(
            {"logical_key_hash": self.logical_key_hash, "canonical_hash": self.canonical_hash}
        )

    @property
    def retrieval_hash(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class ProspectiveOutcomeRetrieval(BaseModel):
    """One append-only observation of the outcome, kept outside decision snapshots."""

    model_config = ConfigDict(frozen=True)

    source: Literal["alpaca"] = "alpaca"
    reality_symbol: str
    native_ticker: str
    endpoint: str
    field_name: Literal["FIRST_1M_BAR_OPEN"] = "FIRST_1M_BAR_OPEN"
    role: Literal["FUTURE_OUTCOME"] = "FUTURE_OUTCOME"
    decision_timestamp: datetime
    event_time: datetime
    request_time: datetime
    ingestion_time: datetime
    provider_identifiers: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any]
    canonical_value: dict[str, Any]
    collector_version: str = OUTCOME_TRANSFORMATION_VERSION
    git_commit: str

    @field_validator("decision_timestamp", "event_time", "request_time", "ingestion_time")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return _utc(value, "outcome timestamp")

    @model_validator(mode="after")
    def validate_ordering(self) -> ProspectiveOutcomeRetrieval:
        decision = _utc(self.decision_timestamp, "decision_timestamp")
        event = _utc(self.event_time, "event_time")
        requested = _utc(self.request_time, "request_time")
        ingested = _utc(self.ingestion_time, "ingestion_time")
        if event <= decision:
            raise ValueError("outcome event must follow the decision")
        if requested < event or ingested < requested:
            raise ValueError("outcome request and ingestion must follow the event")
        if not self.reality_symbol or not self.native_ticker or len(self.git_commit) < 7:
            raise ValueError("outcome identity is incomplete")
        return self

    @property
    def logical_key_hash(self) -> str:
        return canonical_digest(
            {
                "source": self.source,
                "native_ticker": self.native_ticker,
                "field_name": self.field_name,
                "event_time": self.event_time.astimezone(UTC).isoformat(),
                "collector_version": self.collector_version,
            }
        )

    @property
    def canonical_hash(self) -> str:
        return canonical_digest(self.canonical_value)

    @property
    def version_hash(self) -> str:
        return canonical_digest(
            {"logical_key_hash": self.logical_key_hash, "canonical_hash": self.canonical_hash}
        )

    @property
    def retrieval_hash(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class DecisionTimeSnapshot(BaseModel):
    """Exact feature evidence known by a decision time; outcomes cannot enter the schema."""

    model_config = ConfigDict(frozen=True)

    snapshot_version: str
    transformation_version: str = SNAPSHOT_TRANSFORMATION_VERSION
    decision_timestamp: datetime
    reality_observation_versions: tuple[str, ...]
    previous_close_versions: tuple[str, ...]
    source_session_evidence: dict[str, Any]
    source_session_evidence_version: str
    calendar_version: str
    mapping_version: str
    dataset_version: str
    capture_version: str
    contains_future_outcome: Literal[False] = False

    @field_validator("decision_timestamp")
    @classmethod
    def normalize_decision_utc(cls, value: datetime) -> datetime:
        return _utc(value, "decision_timestamp")


def build_decision_snapshot(
    *,
    decision_timestamp: datetime,
    retrievals: tuple[ProspectiveRetrieval, ...],
    source_session_evidence: dict[str, Any],
    source_session_evidence_version: str,
    calendar_version: str,
    mapping_version: str,
    dataset_version: str,
) -> DecisionTimeSnapshot:
    decision = _utc(decision_timestamp, "decision_timestamp")
    if not retrievals:
        raise ValueError("snapshot requires feature observations")
    if any(item.ingestion_time.astimezone(UTC) > decision for item in retrievals):
        raise ValueError("observation was not ingested by decision time")
    if any(item.role != "FEATURE" for item in retrievals):
        raise ValueError("future outcomes are forbidden from decision snapshots")

    reality = tuple(
        sorted(
            item.version_hash for item in retrievals if item.field_name == "REALITY_DECISION_MARK"
        )
    )
    closes = tuple(
        sorted(
            item.version_hash for item in retrievals if item.field_name == "PREVIOUS_NATIVE_CLOSE"
        )
    )
    if not reality or not closes:
        raise ValueError("snapshot requires Reality marks and previous native closes")
    if len(reality) != len(closes):
        raise ValueError("snapshot requires one Reality mark and previous close per instrument")
    capture_version = canonical_digest(sorted(item.retrieval_hash for item in retrievals))
    identity = {
        "transformation_version": SNAPSHOT_TRANSFORMATION_VERSION,
        "decision_timestamp": decision.isoformat(),
        "reality_observation_versions": reality,
        "previous_close_versions": closes,
        "source_session_evidence": source_session_evidence,
        "source_session_evidence_version": source_session_evidence_version,
        "calendar_version": calendar_version,
        "mapping_version": mapping_version,
        "dataset_version": dataset_version,
        "capture_version": capture_version,
        "contains_future_outcome": False,
    }
    return DecisionTimeSnapshot(snapshot_version=canonical_digest(identity), **identity)
