"""Deterministic metadata and private archives for the fixed Phase 1 dataset."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import suppress
from dataclasses import asdict
from datetime import date, datetime, timedelta
from importlib.metadata import version
from pathlib import Path

from sessionzero_market_data import XnysTradingCalendar, load_bitget_source_session_evidence
from sessionzero_market_data.native import (
    NativeCandle,
    NativeDataError,
    NativeHistory,
    NativeInstrument,
    NativePage,
)
from sessionzero_schemas import EvidenceQualifiedCohort

METADATA = Path("datasets/phase1")
ARCHIVES = Path(".local-data/phase1")
TRANSFORMATION = "phase1_dataset.v1"
TARGET_DEFINITION = "cash_boundary_minute.v1"
STATUSES = (
    "TARGET_AVAILABLE",
    "OPEN_MISSING",
    "CLOSE_MISSING",
    "BOTH_MISSING",
    "PROVIDER_FAILURE",
    "STRUCTURAL_FAILURE",
    "UNKNOWN",
)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def write_json(path: Path, value: object, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    # A new file is written atomically; existing archives are never silently overwritten.
    temporary = path.with_suffix(path.suffix + ".pending")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600 if private else 0o644)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load_cohort(path: Path = METADATA / "cohort.json") -> EvidenceQualifiedCohort:
    artifact = json.loads(path.read_text())
    cohort = EvidenceQualifiedCohort.model_validate(artifact["cohort"])
    identity = cohort.model_dump(mode="json", exclude={"cohort_version"})
    # Match the accepted v1 derivation's ISO spelling, including +00:00.
    for name in ("evaluation_start", "evaluation_end"):
        identity[name] = getattr(cohort, name).isoformat()
    if digest(identity) != cohort.cohort_version:
        raise NativeDataError("COHORT_ARTIFACT_HASH_MISMATCH")
    evidence = load_bitget_source_session_evidence()
    record = next(r for r in evidence.evidence if r.evidence_id == artifact["evidence_id"])
    mapping = {m["reality_symbol"]: m["native_ticker"] for m in artifact["mappings"]}
    if (
        len(cohort.members) != 21
        or set(record.symbols) != {m.symbol for m in cohort.members}
        or len(mapping) != 21
        or any(mapping.get(m.symbol) != m.native_ticker for m in cohort.members)
        or evidence.transformation_version != cohort.source_session_evidence_version
        or digest(record.model_dump(mode="json")) != artifact["evidence_record_digest"]
    ):
        raise NativeDataError("COHORT_ARTIFACT_EVIDENCE_OR_MAPPING_MISMATCH")
    return cohort


def calendar_artifact(cohort: EvidenceQualifiedCohort) -> dict:
    calendar = XnysTradingCalendar()
    start, end = cohort.evaluation_start, cohort.evaluation_end
    days = []
    day = start.date()
    while day <= end.date():
        with suppress(ValueError):
            s = calendar.session_on(day)
            if s.regular_open < end and s.regular_close > start:
                days.append(day)
        day += timedelta(days=1)
    core = set(days)
    days.extend(
        [
            calendar.session_at(start).previous_cash_close.date(),
            calendar.session_at(end).next_cash_open.date(),
        ]
    )
    sessions = []
    for day in sorted(set(days)):
        s = calendar.session_on(day)
        sessions.append(
            {
                "session_date": str(day),
                "regular_open": s.regular_open.isoformat(),
                "regular_close": s.regular_close.isoformat(),
                "role": "EVALUATION" if day in core else "BOUNDARY_ANCHOR",
            }
        )
    value = {
        "provider": "exchange_calendars",
        "provider_version": version("exchange-calendars"),
        "calendar": "XNYS",
        "sessions": sessions,
    }
    return {**value, "calendar_version": digest(value)}


def encode_history(history: NativeHistory) -> dict:
    value = asdict(history)
    value["instrument"] = history.instrument.model_dump(mode="json")
    value["candles"] = [c.model_dump(mode="json") for c in history.candles]
    return json.loads(json.dumps(value, default=str))


def decode_history(value: dict) -> NativeHistory:
    return NativeHistory(
        instrument=NativeInstrument.model_validate(value["instrument"]),
        start=datetime.fromisoformat(value["start"]),
        end=datetime.fromisoformat(value["end"]),
        pages=tuple(
            NativePage(**{**p, "ingestion_time": datetime.fromisoformat(p["ingestion_time"])})
            for p in value["pages"]
        ),
        candles=tuple(NativeCandle.model_validate(c) for c in value["candles"]),
        source=value["source"],
        clipped_count=value["clipped_count"],
    )


def pair_status(open_status: str, close_status: str) -> str:
    for failure in ("STRUCTURAL_FAILURE", "PROVIDER_FAILURE", "UNKNOWN"):
        if failure in (open_status, close_status):
            return failure
    if (open_status, close_status) == ("AVAILABLE", "AVAILABLE"):
        return "TARGET_AVAILABLE"
    if (open_status, close_status) == ("MISSING_BOUNDARY_MINUTE", "MISSING_BOUNDARY_MINUTE"):
        return "BOTH_MISSING"
    if (open_status, close_status) == ("MISSING_BOUNDARY_MINUTE", "AVAILABLE"):
        return "OPEN_MISSING"
    if (open_status, close_status) == ("AVAILABLE", "MISSING_BOUNDARY_MINUTE"):
        return "CLOSE_MISSING"
    return "UNKNOWN"


def target_date(value: str) -> date:
    return date.fromisoformat(value)
