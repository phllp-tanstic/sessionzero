import copy
import json
from datetime import UTC, datetime

import pytest
from sessionzero_database.dataset import materialize, persist_manifest, persist_target
from sessionzero_database.dataset_artifacts import write_json
from sessionzero_database.models import (
    NativeSessionTarget,
    NormalizedNativeEquityCandle,
    Phase1DatasetManifest,
    Phase1DatasetReality,
    Phase1DatasetTarget,
    RawNativeEquityObservation,
)
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.postgres


def test_target_idempotency_and_correction_lineage(database_engine, phase1_fixture):
    cohort, calendar, captured, make = phase1_fixture
    row = make()
    first = persist_target(database_engine, row, cohort, calendar, captured_at=captured)
    assert persist_target(database_engine, row, cohort, calendar, captured_at=captured) == first
    changed = copy.deepcopy(row)
    changed["open"]["history"]["candles"][0]["open"] = "100.5"
    raw = json.loads(changed["open"]["history"]["pages"][0]["body"])
    raw["bars"][0]["o"] = "100.5"
    changed["open"]["history"]["pages"][0]["body"] = json.dumps(raw)
    second = persist_target(database_engine, changed, cohort, calendar, captured_at=captured)
    assert second != first
    with database_engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(NativeSessionTarget)) == 2
        assert c.scalar(select(func.count()).select_from(RawNativeEquityObservation)) == 4
        assert c.scalar(select(func.count()).select_from(NormalizedNativeEquityCandle)) == 3
        target = (
            c.execute(
                select(NativeSessionTarget).where(NativeSessionTarget.target_version == first)
            )
            .mappings()
            .one()
        )
        assert target["open_raw_id"] is not None and target["open_candle_id"] is not None
        assert target["open_run_id"] is not None and target["ingestion_time"] == captured
        assert target["provenance"]["identity"]["open_definition"] == "FIRST_1M_BAR_OPEN"
    with pytest.raises(IntegrityError), database_engine.begin() as c:
        c.execute(insert(NativeSessionTarget).values(**target))


@pytest.mark.parametrize(
    "missing,status",
    [
        (("open",), "OPEN_MISSING"),
        (("close",), "CLOSE_MISSING"),
        (("open", "close"), "BOTH_MISSING"),
    ],
)
def test_missing_persistence_retains_empty_raw(database_engine, phase1_fixture, missing, status):
    cohort, calendar, captured, make = phase1_fixture
    v = persist_target(
        database_engine, make(missing=missing), cohort, calendar, captured_at=captured
    )
    with database_engine.connect() as c:
        target = (
            c.execute(select(NativeSessionTarget).where(NativeSessionTarget.target_version == v))
            .mappings()
            .one()
        )
        assert target["status"] == status
        for leg in missing:
            assert target[f"{leg}_target"] is None
            assert target[f"{leg}_candle_id"] is None
            assert target[f"{leg}_raw_id"] is not None


def test_provider_failure_is_not_both_missing(database_engine, phase1_fixture):
    cohort, calendar, captured, make = phase1_fixture
    row = make()
    row["open"] = {"status": "PROVIDER_FAILURE", "error_code": "AUTHENTICATION_OR_ENTITLEMENT"}
    v = persist_target(database_engine, row, cohort, calendar, captured_at=captured)
    with database_engine.connect() as c:
        target = (
            c.execute(select(NativeSessionTarget).where(NativeSessionTarget.target_version == v))
            .mappings()
            .one()
        )
        assert target["status"] == "PROVIDER_FAILURE"
        assert target["open_run_id"] is not None and target["open_raw_id"] is None
        assert target["close_target"] is not None


def test_materialization_version_joinability_and_repeat(database_engine, phase1_fixture, tmp_path):
    cohort, calendar, captured, make = phase1_fixture
    # Deliberately tiny synthetic fixture exercises real DB linkage without provider calls.
    cohort = cohort.model_copy(update={"members": (cohort.members[0],)})
    calendar = copy.deepcopy(calendar)
    calendar["sessions"] = [calendar["sessions"][i] for i in (0, 1, -2, -1)]
    member = cohort.members[0]
    write_json(tmp_path / "collection.json", {"finished_at": captured.isoformat()})
    write_json(
        tmp_path / f"native-{member.symbol}.json",
        {
            "rows": [make(s) for s in calendar["sessions"]],
            "telemetry": {"requests": 8, "retries": 0, "rate_limits": 0},
        },
    )
    from sessionzero_schemas import MarketCandle

    observations = []
    for event in (datetime(2026, 6, 15, 20, tzinfo=UTC), datetime(2026, 9, 11, 20, tzinfo=UTC)):
        candle = MarketCandle(
            symbol=member.symbol,
            market="SPOT",
            event_time=event,
            interval="1H",
            ingestion_time=captured,
            open=100,
            high=102,
            low=99,
            close=101,
        )
        observations.append(
            {
                "candle": candle.model_dump(mode="json"),
                "payload": ["TEST_ONLY"],
                "endpoint": "/SYNTHETIC",
            }
        )
    write_json(
        tmp_path / f"reality-{member.symbol}.json",
        {
            "observations": observations,
            "quality": {
                "structural_quality_status": "PASS",
                "quality_status": "PASS",
                "page_count": 1,
            },
        },
    )
    first, targets, reality = materialize(
        database_engine, cohort, calendar, tmp_path, code_provenance={}
    )
    persist_manifest(database_engine, first, targets, reality)
    second, targets2, reality2 = materialize(
        database_engine, cohort, calendar, tmp_path, code_provenance={}
    )
    persist_manifest(database_engine, second, targets2, reality2)
    assert first["dataset_version"] == second["dataset_version"]
    assert first["generated_at"] != second["generated_at"]
    assert first["phase1_exit"] == "YES" and first["summary"]["unresolved_joins"] == []
    with database_engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(Phase1DatasetManifest)) == 1
        assert c.scalar(select(func.count()).select_from(Phase1DatasetTarget)) == 4
        assert c.scalar(select(func.count()).select_from(Phase1DatasetReality)) == 2
        assert c.scalar(select(Phase1DatasetReality.next_open_role).limit(1)) == "FUTURE_OUTCOME"
