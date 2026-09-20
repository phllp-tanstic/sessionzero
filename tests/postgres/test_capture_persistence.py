import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sessionzero_database.capture import persist_point_in_time_capture
from sessionzero_database.models import (
    DecisionTimeSnapshotRow,
    PointInTimeCaptureRun,
    PointInTimeObservationVersion,
    PointInTimeRetrieval,
)
from sessionzero_schemas import ProspectiveRetrieval, build_decision_snapshot
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.postgres
DECISION = datetime(2026, 9, 21, 12, 30, tzinfo=UTC)


def item(field, *, value="100", minute=5):
    return ProspectiveRetrieval(
        source="bitget" if field == "REALITY_DECISION_MARK" else "alpaca",
        symbol="RAAPLUSDT",
        endpoint="/synthetic-test",
        field_name=field,
        event_time=DECISION - timedelta(hours=2),
        request_time=DECISION - timedelta(minutes=minute),
        ingestion_time=DECISION - timedelta(minutes=minute - 1),
        provider_identifiers={"request_id": f"synthetic-{minute}"},
        raw_response={"test_only": True, "value": value, "minute": minute},
        canonical_value={"close": value},
        git_commit="a" * 40,
    )


def snapshot(retrievals):
    return build_decision_snapshot(
        decision_timestamp=DECISION,
        retrievals=retrievals,
        source_session_evidence={"RAAPLUSDT": {"evidence_ids": ["synthetic"]}},
        source_session_evidence_version="source.v1",
        calendar_version="c" * 64,
        mapping_version="m" * 64,
        dataset_version="d" * 64,
    )


def persist(database_engine, retrievals):
    return persist_point_in_time_capture(
        database_engine,
        capture_id=uuid.uuid4(),
        started_at=DECISION - timedelta(minutes=10),
        completed_at=DECISION - timedelta(minutes=1),
        retrievals=retrievals,
        snapshot=snapshot(retrievals),
    )


def test_same_refetch_retains_raw_evidence_and_reuses_version(database_engine):
    first = (item("REALITY_DECISION_MARK"), item("PREVIOUS_NATIVE_CLOSE"))
    second = (
        item("REALITY_DECISION_MARK", minute=3),
        item("PREVIOUS_NATIVE_CLOSE", minute=3),
    )
    assert persist(database_engine, first)["observation_versions_written"] == 2
    assert persist(database_engine, second)["observation_versions_written"] == 0
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(PointInTimeCaptureRun)) == 2
        assert connection.scalar(select(func.count()).select_from(PointInTimeRetrieval)) == 4
        assert (
            connection.scalar(select(func.count()).select_from(PointInTimeObservationVersion)) == 2
        )
        assert connection.scalar(select(func.count()).select_from(DecisionTimeSnapshotRow)) == 2


def test_provider_revision_appends_version(database_engine):
    first = (item("REALITY_DECISION_MARK"), item("PREVIOUS_NATIVE_CLOSE"))
    revised = (
        item("REALITY_DECISION_MARK", value="101", minute=3),
        item("PREVIOUS_NATIVE_CLOSE", minute=3),
    )
    persist(database_engine, first)
    assert persist(database_engine, revised)["observation_versions_written"] == 1
    with database_engine.connect() as connection:
        assert (
            connection.scalar(select(func.count()).select_from(PointInTimeObservationVersion)) == 3
        )


def test_database_rejects_update_and_delete(database_engine):
    retrievals = (item("REALITY_DECISION_MARK"), item("PREVIOUS_NATIVE_CLOSE"))
    result = persist(database_engine, retrievals)
    with pytest.raises(DBAPIError, match="append-only"), database_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE decision_time_snapshots SET dataset_version = :changed "
                "WHERE snapshot_version = :version"
            ),
            {"changed": "z" * 64, "version": result["snapshot_version"]},
        )
    with pytest.raises(DBAPIError, match="append-only"), database_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM point_in_time_capture_runs WHERE capture_id = :capture_id"),
            {"capture_id": result["capture_id"]},
        )
