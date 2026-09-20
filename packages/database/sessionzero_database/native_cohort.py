"""Reverify an existing cohort identity without creating/relabeling a universe snapshot."""

from __future__ import annotations

import hashlib
import json
import re

from sessionzero_bitget import BitgetReferenceDataProvider
from sessionzero_bitget.evidence_cohort import (
    EVIDENCE_COHORT_DERIVATION_VERSION,
    EVIDENCE_COHORT_EVALUATION_END,
    EVIDENCE_COHORT_EVALUATION_START,
    EVIDENCE_COHORT_INTERVAL,
)
from sessionzero_market_data import load_bitget_source_session_evidence
from sessionzero_market_data.native import NativeDataError
from sessionzero_schemas import EvidenceQualifiedCohort, EvidenceQualifiedCohortMember


def reverify_native_cohort(
    provider: BitgetReferenceDataProvider,
    *,
    evidence_id: str,
    original_universe_version: str,
    expected_cohort_version: str,
) -> tuple[EvidenceQualifiedCohort, tuple]:
    """The supplied universe hash is a historical reference, never a newly built snapshot."""
    if not all(
        re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (original_universe_version, expected_cohort_version)
    ):
        raise NativeDataError("FULL_ACCEPTED_IDENTITY_REQUIRED")
    dataset = load_bitget_source_session_evidence()
    record = next((r for r in dataset.evidence if r.evidence_id == evidence_id), None)
    if (
        record is None
        or len(record.symbols) != 21
        or "*" in record.symbols
        or record.effective_from > EVIDENCE_COHORT_EVALUATION_START
        or (
            record.effective_to is not None and record.effective_to < EVIDENCE_COHORT_EVALUATION_END
        )
    ):
        raise NativeDataError("ACCEPTED_MEMBERSHIP_EVIDENCE_REQUIRED")
    members, raw = [], []
    for symbol in sorted(record.symbols):
        mapping, evidence = provider.get_mapping(symbol)
        members.append(
            EvidenceQualifiedCohortMember(
                symbol=symbol,
                native_ticker=mapping.native_ticker,
                source_session_evidence_ids=(record.evidence_id,),
            )
        )
        raw.extend(evidence)
    identity = {
        "derivation_version": EVIDENCE_COHORT_DERIVATION_VERSION,
        "universe_version": original_universe_version,
        "source_session_evidence_version": dataset.transformation_version,
        "interval": EVIDENCE_COHORT_INTERVAL,
        "evaluation_start": EVIDENCE_COHORT_EVALUATION_START.isoformat(),
        "evaluation_end": EVIDENCE_COHORT_EVALUATION_END.isoformat(),
        "members": [m.model_dump(mode="json") for m in members],
    }
    version = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    if version != expected_cohort_version:
        raise NativeDataError(
            "ACCEPTED_COHORT_HASH_MISMATCH",
            details={
                "expected_cohort_version": expected_cohort_version,
                "recomputed_cohort_version": version,
            },
        )
    cohort = EvidenceQualifiedCohort(
        **identity,
        cohort_version=version,
    )
    return cohort, tuple(raw)
