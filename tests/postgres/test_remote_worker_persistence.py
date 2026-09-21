import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sessionzero_database.capture import persist_point_in_time_capture
from sessionzero_database.models import (
    DecisionOutcomeLink,
    DecisionTimeSnapshotRow,
    ProspectiveOutcomeRetrievalRow,
    ProspectiveOutcomeVersion,
    ProspectiveWorkerRun,
)
from sessionzero_database.outcome import persist_prospective_outcomes
from sessionzero_schemas import (
    ProspectiveOutcomeRetrieval,
    ProspectiveRetrieval,
    build_decision_snapshot,
)
from sessionzero_worker.main import run_tick, worker_status
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.postgres
DECISION = datetime(2026, 9, 21, 12, 30, tzinfo=UTC)
OPEN = datetime(2026, 9, 21, 13, 30, tzinfo=UTC)


def feature(field, *, minute=5):
    return ProspectiveRetrieval(
        source="bitget" if field == "REALITY_DECISION_MARK" else "alpaca",
        symbol="RAAPLUSDT",
        endpoint="/synthetic",
        field_name=field,
        event_time=DECISION - timedelta(hours=2),
        request_time=DECISION - timedelta(minutes=minute),
        ingestion_time=DECISION - timedelta(minutes=minute - 1),
        raw_response={"test_only": True, "minute": minute},
        canonical_value={"close": "100"},
        git_commit="a" * 40,
    )


def store_snapshot(database_engine, minute=5):
    retrievals = (
        feature("REALITY_DECISION_MARK", minute=minute),
        feature("PREVIOUS_NATIVE_CLOSE", minute=minute),
    )
    snapshot = build_decision_snapshot(
        decision_timestamp=DECISION,
        retrievals=retrievals,
        source_session_evidence={"RAAPLUSDT": {"test_only": True}},
        source_session_evidence_version="source.v1",
        calendar_version="c" * 64,
        mapping_version="m" * 64,
        dataset_version="d" * 64,
    )
    return persist_point_in_time_capture(
        database_engine,
        capture_id=uuid.uuid4(),
        started_at=DECISION - timedelta(minutes=10),
        completed_at=DECISION - timedelta(minutes=1),
        retrievals=retrievals,
        snapshot=snapshot,
    )


def outcome(*, value="100", minute=47):
    return ProspectiveOutcomeRetrieval(
        reality_symbol="RAAPLUSDT",
        native_ticker="AAPL",
        endpoint="/synthetic-bars",
        decision_timestamp=DECISION,
        event_time=OPEN,
        request_time=OPEN + timedelta(minutes=minute),
        ingestion_time=OPEN + timedelta(minutes=minute, seconds=1),
        provider_identifiers={"request_id": f"synthetic-{minute}"},
        raw_response={"test_only": True, "minute": minute, "value": value},
        canonical_value={"open": value, "feed": "sip", "adjustment": "raw"},
        git_commit="a" * 40,
    )


def persist_outcome(database_engine, snapshot_version, item):
    return persist_prospective_outcomes(
        database_engine,
        capture_id=uuid.uuid4(),
        snapshot_version=snapshot_version,
        decision_timestamp=DECISION,
        scheduled_open=OPEN,
        started_at=OPEN + timedelta(minutes=46),
        completed_at=OPEN + timedelta(minutes=48),
        retrievals=(item,),
    )


def test_outcome_refetch_and_revision_are_append_only(database_engine):
    snapshot_version = store_snapshot(database_engine)["snapshot_version"]
    first = persist_outcome(database_engine, snapshot_version, outcome())
    exact_repeat = persist_outcome(database_engine, snapshot_version, outcome())
    repeated = persist_outcome(database_engine, snapshot_version, outcome(minute=49))
    revised = persist_outcome(database_engine, snapshot_version, outcome(value="101", minute=51))
    assert first["outcome_versions_written"] == 1
    assert exact_repeat["retrievals_written"] == 0
    assert repeated["outcome_versions_written"] == 0
    assert repeated["outcome_links_written"] == 0
    assert revised["outcome_versions_written"] == revised["outcome_links_written"] == 1
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(ProspectiveOutcomeVersion)) == 2
        retrieval_count = connection.scalar(
            select(func.count()).select_from(ProspectiveOutcomeRetrievalRow)
        )
        assert retrieval_count == 3
        assert connection.scalar(select(func.count()).select_from(DecisionOutcomeLink)) == 2
    with pytest.raises(DBAPIError, match="append-only"), database_engine.begin() as connection:
        connection.execute(text("DELETE FROM decision_outcome_links"))


def test_duplicate_decision_invocation_keeps_one_snapshot(database_engine):
    first = store_snapshot(database_engine, minute=5)
    exact_repeat = store_snapshot(database_engine, minute=5)
    second = store_snapshot(database_engine, minute=3)
    assert first["snapshot_created"] is True
    assert exact_repeat["retrievals_written"] == 0
    assert second["snapshot_created"] is False
    assert first["snapshot_version"] == second["snapshot_version"]
    assert second["retrievals_written"] == 2
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(DecisionTimeSnapshotRow)) == 1


def test_worker_restart_uses_existing_snapshot_without_provider_call(database_engine):
    cohort_mapping = (
        __import__("sessionzero_database.dataset_artifacts", fromlist=["load_cohort"])
        .load_cohort()
        .cohort_version
    )

    def production_runner(**kwargs):
        retrievals = (feature("REALITY_DECISION_MARK"), feature("PREVIOUS_NATIVE_CLOSE"))
        snapshot = build_decision_snapshot(
            decision_timestamp=DECISION,
            retrievals=retrievals,
            source_session_evidence={"RAAPLUSDT": {"test_only": True}},
            source_session_evidence_version="source.v1",
            calendar_version="c" * 64,
            mapping_version=cohort_mapping,
            dataset_version="d" * 64,
        )
        return persist_point_in_time_capture(
            database_engine,
            capture_id=uuid.uuid4(),
            started_at=DECISION - timedelta(minutes=10),
            completed_at=DECISION - timedelta(minutes=1),
            retrievals=retrievals,
            snapshot=snapshot,
        )

    first = run_tick(
        now=DECISION - timedelta(minutes=10),
        engine=database_engine,
        decision_runner=production_runner,
        commit="a" * 40,
    )
    second = run_tick(
        now=DECISION - timedelta(minutes=5),
        engine=database_engine,
        decision_runner=lambda **kwargs: pytest.fail("provider should not be called after restart"),
        commit="a" * 40,
    )
    assert first["status"] == second["status"] == "SUCCEEDED"
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(DecisionTimeSnapshotRow)) == 1
        assert connection.scalar(select(func.count()).select_from(ProspectiveWorkerRun)) == 2
    status = worker_status(database_engine)
    assert status["migration_head"] == "20260921_11"
    assert status["latest_snapshot"] == first["snapshot_version"]
    assert status["latest_outcome_links"] == 0


def test_partial_provider_failure_is_explicit(database_engine):
    class PartialFailure(RuntimeError):
        completed_symbols = 4

    result = run_tick(
        now=DECISION - timedelta(minutes=10),
        engine=database_engine,
        decision_runner=lambda **kwargs: (_ for _ in ()).throw(PartialFailure()),
        commit="a" * 40,
    )
    assert result["status"] == "PARTIAL"
    assert result["symbols_captured"] == 4


def test_identity_mismatch_fails_closed(database_engine, monkeypatch):
    monkeypatch.setattr(
        "sessionzero_worker.main.load_cohort",
        lambda: (_ for _ in ()).throw(ValueError("test mismatch")),
    )
    result = run_tick(
        now=DECISION - timedelta(minutes=10),
        engine=database_engine,
        commit="a" * 40,
    )
    assert result["status"] == "IDENTITY_MISMATCH"
    assert result["symbols_captured"] == 0


def test_existing_snapshot_mapping_mismatch_fails_closed(database_engine):
    store_snapshot(database_engine)
    result = run_tick(
        now=DECISION - timedelta(minutes=5),
        engine=database_engine,
        decision_runner=lambda **kwargs: pytest.fail("mismatched snapshot is not reusable"),
        commit="a" * 40,
    )
    assert result["status"] == "IDENTITY_MISMATCH"
    assert result["error_code"] == "SNAPSHOT_MAPPING_MISMATCH"


def test_late_worker_records_missed_without_calling_provider(database_engine):
    result = run_tick(
        now=OPEN,
        engine=database_engine,
        outcome_runner=lambda **kwargs: pytest.fail("outcome cannot run without snapshot"),
        commit="a" * 40,
    )
    assert result["status"] == "MISSED_DECISION_WINDOW"
    assert result["error_code"] == "NO_SNAPSHOT_AT_DECISION"
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(DecisionTimeSnapshotRow)) == 0
        run = connection.execute(
            select(ProspectiveWorkerRun.status, ProspectiveWorkerRun.error_code)
        ).one()
        assert run == ("MISSED_DECISION_WINDOW", "NO_SNAPSHOT_AT_DECISION")
