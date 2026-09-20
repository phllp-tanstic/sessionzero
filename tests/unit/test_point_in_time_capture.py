from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sessionzero_database.capture_cli import validate_capture_window
from sessionzero_schemas import (
    ProspectiveRetrieval,
    RevisionIntegrityStatus,
    build_decision_snapshot,
)

DECISION = datetime(2026, 9, 21, 12, 30, tzinfo=UTC)


def retrieval(
    field_name="REALITY_DECISION_MARK",
    *,
    value="100",
    request_time=DECISION - timedelta(minutes=5),
    ingestion_time=DECISION - timedelta(minutes=4),
):
    source = "bitget" if field_name == "REALITY_DECISION_MARK" else "alpaca"
    return ProspectiveRetrieval(
        source=source,
        symbol="RAAPLUSDT",
        endpoint="/history",
        field_name=field_name,
        event_time=DECISION - timedelta(hours=1, minutes=30),
        request_time=request_time,
        ingestion_time=ingestion_time,
        provider_identifiers={"request_id": "synthetic-test"},
        raw_response={"test_only": True, "value": value},
        canonical_value={"close": value},
        git_commit="a" * 40,
    )


def snapshot(items):
    return build_decision_snapshot(
        decision_timestamp=DECISION,
        retrievals=tuple(items),
        source_session_evidence={"RAAPLUSDT": {"evidence_ids": ["test"]}},
        source_session_evidence_version="source.v1",
        calendar_version="c" * 64,
        mapping_version="m" * 64,
        dataset_version="d" * 64,
    )


def test_models_are_immutable():
    item = retrieval()
    with pytest.raises(ValidationError):
        item.canonical_value = {"close": "999"}


def test_same_observation_refetch_reuses_version_but_retains_retrieval_identity():
    first = retrieval()
    second = retrieval(
        request_time=DECISION - timedelta(minutes=3),
        ingestion_time=DECISION - timedelta(minutes=2),
    )
    assert first.version_hash == second.version_hash
    assert first.retrieval_hash != second.retrieval_hash


def test_provider_revision_creates_new_version():
    assert retrieval(value="100").logical_key_hash == retrieval(value="101").logical_key_hash
    assert retrieval(value="100").version_hash != retrieval(value="101").version_hash


def test_ingestion_time_ordering_is_enforced():
    with pytest.raises(ValidationError, match="ingestion_time cannot precede"):
        retrieval(
            request_time=DECISION - timedelta(minutes=1),
            ingestion_time=DECISION - timedelta(minutes=2),
        )


def test_decision_time_filters_late_availability():
    late = retrieval(ingestion_time=DECISION + timedelta(microseconds=1))
    with pytest.raises(ValueError, match="not ingested by decision"):
        snapshot([late, retrieval("PREVIOUS_NATIVE_CLOSE")])


def test_future_outcome_cannot_be_constructed_or_enter_snapshot():
    with pytest.raises(ValidationError):
        ProspectiveRetrieval(
            source="alpaca",
            symbol="RAAPLUSDT",
            endpoint="/history",
            field_name="NEXT_NATIVE_OPEN",
            role="OUTCOME",
            event_time=DECISION + timedelta(hours=1),
            request_time=DECISION,
            ingestion_time=DECISION,
            raw_response={},
            canonical_value={},
            git_commit="a" * 40,
        )


def test_snapshot_is_deterministic_and_order_independent():
    mark, close = retrieval(), retrieval("PREVIOUS_NATIVE_CLOSE")
    first, second = snapshot([mark, close]), snapshot([close, mark])
    assert first == second
    assert not first.contains_future_outcome


def test_snapshot_requires_both_feature_families():
    with pytest.raises(ValueError, match="requires Reality marks and previous native closes"):
        snapshot([retrieval()])


def test_snapshot_requires_paired_feature_counts():
    with pytest.raises(ValueError, match="one Reality mark and previous close per instrument"):
        snapshot(
            [
                retrieval(),
                retrieval("PREVIOUS_NATIVE_CLOSE"),
                retrieval("PREVIOUS_NATIVE_CLOSE", value="101"),
            ]
        )


def test_revision_and_claim_statuses_do_not_collapse_unknown():
    values = {item.value for item in RevisionIntegrityStatus}
    assert values == {
        "POINT_IN_TIME_VERIFIED",
        "REVISION_POSSIBLE",
        "REVISION_POLICY_UNKNOWN",
        "RETROSPECTIVE_ONLY",
        "PROSPECTIVELY_SAFE",
    }
    assert RevisionIntegrityStatus.REVISION_POLICY_UNKNOWN != (
        RevisionIntegrityStatus.POINT_IN_TIME_VERIFIED
    )
    assert RevisionIntegrityStatus.RETROSPECTIVE_ONLY != RevisionIntegrityStatus.PROSPECTIVELY_SAFE


def test_capture_window_rejects_historical_final_oos_before_provider_access():
    final_oos_decision = datetime(2026, 8, 17, 12, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="predeclared pre-decision window"):
        validate_capture_window(
            decision_timestamp=final_oos_decision,
            now=datetime(2026, 9, 20, tzinfo=UTC),
        )


def test_capture_window_accepts_only_predecision_interval():
    validate_capture_window(decision_timestamp=DECISION, now=DECISION - timedelta(minutes=5))
    for now in (DECISION - timedelta(minutes=11), DECISION + timedelta(microseconds=1)):
        with pytest.raises(ValueError):
            validate_capture_window(decision_timestamp=DECISION, now=now)
