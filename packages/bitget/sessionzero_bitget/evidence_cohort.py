from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sessionzero_market_data import (
    CuratedBitgetSourceSessionProvider,
    SourceSessionCapabilityKind,
    SourceSessionEvidenceConfidence,
    SourceSessionEvidenceDataset,
    SourceSessionEvidenceType,
    SourceSessionMode,
    SourceSessionResolutionStatus,
)
from sessionzero_schemas import (
    EvidenceQualifiedCohort,
    EvidenceQualifiedCohortMember,
    UniverseMember,
)

EVIDENCE_COHORT_DERIVATION_VERSION = "evidence_qualified_cohort.v1"
EVIDENCE_COHORT_INTERVAL = "1H"
EVIDENCE_COHORT_EVALUATION_START = datetime(2026, 6, 15, 20, tzinfo=UTC)
EVIDENCE_COHORT_EVALUATION_END = datetime(2026, 9, 13, 20, tzinfo=UTC)


def _hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _conflict_checkpoints(
    dataset: SourceSessionEvidenceDataset, start: datetime, end: datetime
) -> tuple[datetime, ...]:
    points = {start, end - timedelta(microseconds=1)}
    for record in dataset.evidence:
        for boundary in (record.effective_from, record.effective_to):
            if boundary is None:
                continue
            boundary = boundary.astimezone(UTC)
            if start <= boundary < end:
                points.add(boundary)
            after = boundary + timedelta(microseconds=1)
            if start <= after < end:
                points.add(after)
    return tuple(sorted(points))


def derive_evidence_qualified_cohort(
    *,
    universe_version: str,
    universe_members: tuple[UniverseMember, ...],
    evidence_dataset: SourceSessionEvidenceDataset,
    evaluation_start: datetime = EVIDENCE_COHORT_EVALUATION_START,
    evaluation_end: datetime = EVIDENCE_COHORT_EVALUATION_END,
    interval: str = EVIDENCE_COHORT_INTERVAL,
) -> EvidenceQualifiedCohort:
    start = evaluation_start.astimezone(UTC)
    end = evaluation_end.astimezone(UTC)
    if end <= start:
        raise ValueError("cohort evaluation range must be increasing")

    accepted = {member.reality_symbol: member for member in universe_members}
    covering_records = tuple(
        record
        for record in evidence_dataset.evidence
        if record.symbols
        and "*" not in record.symbols
        and record.capability == SourceSessionCapabilityKind.TRADING_SCHEDULE
        and record.session_mode != SourceSessionMode.UNKNOWN
        and record.evidence_type
        in {
            SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
            SourceSessionEvidenceType.DATED_ENUMERATED_STATUS,
        }
        and record.confidence == SourceSessionEvidenceConfidence.VERIFIED_EXPLICIT
        and record.effective_from <= start
        and (record.effective_to is None or record.effective_to >= end)
    )
    evidence_by_symbol: dict[str, set[str]] = {}
    for record in covering_records:
        for symbol in record.symbols:
            evidence_by_symbol.setdefault(symbol, set()).add(record.evidence_id)

    provider = CuratedBitgetSourceSessionProvider(
        evidence=evidence_dataset.evidence,
        transformation_version=evidence_dataset.transformation_version,
    )
    checkpoints = _conflict_checkpoints(evidence_dataset, start, end)
    members: list[EvidenceQualifiedCohortMember] = []
    for symbol in sorted(evidence_by_symbol):
        universe_member = accepted.get(symbol)
        if universe_member is None or universe_member.native_ticker is None:
            continue
        if any(
            provider.session_at(symbol, timestamp).resolution_status
            == SourceSessionResolutionStatus.CONFLICT
            for timestamp in checkpoints
        ):
            continue
        members.append(
            EvidenceQualifiedCohortMember(
                symbol=symbol,
                native_ticker=universe_member.native_ticker,
                source_session_evidence_ids=tuple(sorted(evidence_by_symbol[symbol])),
            )
        )

    identity = {
        "derivation_version": EVIDENCE_COHORT_DERIVATION_VERSION,
        "universe_version": universe_version,
        "source_session_evidence_version": evidence_dataset.transformation_version,
        "interval": interval,
        "evaluation_start": start.isoformat(),
        "evaluation_end": end.isoformat(),
        "members": [member.model_dump(mode="json") for member in members],
    }
    return EvidenceQualifiedCohort(
        cohort_version=_hash(identity),
        derivation_version=EVIDENCE_COHORT_DERIVATION_VERSION,
        universe_version=universe_version,
        source_session_evidence_version=evidence_dataset.transformation_version,
        interval=interval,
        evaluation_start=start,
        evaluation_end=end,
        members=tuple(members),
    )
