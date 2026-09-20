import json
from datetime import UTC, datetime, timedelta

import pytest
from sessionzero_database.dataset import PIT_POLICY, join_context, prepare_target
from sessionzero_database.dataset_artifacts import (
    METADATA,
    calendar_artifact,
    digest,
    load_cohort,
    pair_status,
    write_json,
)
from sessionzero_database.dataset_cli import check_archives
from sessionzero_market_data import XnysTradingCalendar
from sessionzero_market_data.native import NativeDataError


@pytest.mark.parametrize(
    "missing,status",
    [
        ((), "TARGET_AVAILABLE"),
        (("open",), "OPEN_MISSING"),
        (("close",), "CLOSE_MISSING"),
        (("open", "close"), "BOTH_MISSING"),
    ],
)
def test_exact_missing_semantics(phase1_fixture, missing, status):
    cohort, calendar, _, make = phase1_fixture
    identity, histories = prepare_target(make(missing=missing), cohort, calendar)
    assert identity["status"] == status
    assert all(not histories[leg].candles for leg in missing)
    assert identity["adjustment"] == "raw" and identity["feed"] == "sip"


@pytest.mark.parametrize("status", ["PROVIDER_FAILURE", "STRUCTURAL_FAILURE", "UNKNOWN"])
def test_failure_distinct_from_missing(phase1_fixture, status):
    cohort, calendar, _, make = phase1_fixture
    row = make()
    row["open"] = {"status": status, "error_code": "SYNTHETIC_FAILURE"}
    identity, histories = prepare_target(row, cohort, calendar)
    assert identity["status"] == status
    assert "open" not in histories and histories["close"].candles
    assert pair_status("INVALID", "AVAILABLE") == "UNKNOWN"


def test_cohort_reproduces_without_old_database_or_chat(tmp_path):
    cohort = load_cohort()
    assert len(cohort.members) == 21
    assert (
        cohort.cohort_version == "a69d8c427abac466e8b4088f109e55640bc9e5172011ec6b70919b1874176f32"
    )
    value = json.loads((METADATA / "cohort.json").read_text())
    value["cohort"]["universe_version"] = "0" * 64
    write_json(tmp_path / "bad.json", value)
    with pytest.raises(NativeDataError, match="HASH_MISMATCH"):
        load_cohort(tmp_path / "bad.json")
    value = json.loads((METADATA / "cohort.json").read_text())
    value["mappings"][0]["native_ticker"] = "OTHER"
    write_json(tmp_path / "bad.json", value)
    with pytest.raises(NativeDataError, match="EVIDENCE_OR_MAPPING"):
        load_cohort(tmp_path / "bad.json")


def test_calendar_version_and_boundary_anchors():
    calendar = calendar_artifact(load_cohort())
    assert calendar == json.loads((METADATA / "calendar.json").read_text())
    assert sum(s["role"] == "EVALUATION" for s in calendar["sessions"]) == 61
    assert [s["session_date"] for s in calendar["sessions"] if s["role"] == "BOUNDARY_ANCHOR"] == [
        "2026-06-15",
        "2026-09-14",
    ]
    identity = {k: v for k, v in calendar.items() if k != "calendar_version"}
    assert digest(identity) == calendar["calendar_version"]
    identity["provider_version"] = "different"
    assert digest(identity) != calendar["calendar_version"]


@pytest.mark.parametrize(
    "change", ["minute", "feed", "adjustment", "universe", "cohort", "calendar"]
)
def test_no_boundary_substitution_or_contract_fallback(phase1_fixture, change):
    cohort, calendar, _, make = phase1_fixture
    row = make()
    h = row["open"]["history"]
    if change == "minute":
        h["candles"][0]["event_time"] = (
            datetime.fromisoformat(h["start"]) + timedelta(minutes=1)
        ).isoformat()
    elif change == "feed":
        h["pages"][0]["params"]["feed"] = "iex"
    elif change == "adjustment":
        h["pages"][0]["params"]["adjustment"] = "all"
    elif change in ("universe", "cohort"):
        h["instrument"][f"{change}_version"] = "0" * 64
    else:
        row["session"] = {**row["session"], "regular_open": "2026-06-16T13:31:00+00:00"}
    with pytest.raises(NativeDataError):
        prepare_target(row, cohort, calendar)


def test_target_identity_excludes_retrieval_time_but_binds_corrections(phase1_fixture):
    cohort, calendar, _, make = phase1_fixture
    row = make()
    first, _ = prepare_target(row, cohort, calendar)
    for leg in ("open", "close"):
        row[leg]["history"]["candles"][0]["ingestion_time"] = "2026-09-21T00:00:00Z"
        row[leg]["history"]["pages"][0]["ingestion_time"] = "2026-09-21T00:00:00Z"
    repeat, _ = prepare_target(row, cohort, calendar)
    assert digest(first) == digest(repeat)
    row["open"]["history"]["candles"][0]["open"] = "100.5"
    raw = json.loads(row["open"]["history"]["pages"][0]["body"])
    raw["bars"][0]["o"] = "100.5"
    row["open"]["history"]["pages"][0]["body"] = json.dumps(raw)
    corrected, _ = prepare_target(row, cohort, calendar)
    assert digest(first) != digest(corrected)


def test_completed_bar_timestamp_and_future_label():
    calendar = XnysTradingCalendar()
    result = join_context(datetime(2026, 9, 11, 19, tzinfo=UTC), calendar)
    assert result["decision_time"] == datetime(2026, 9, 11, 20, tzinfo=UTC)
    assert str(result["previous_date"]) == "2026-09-11"
    assert str(result["next_date"]) == "2026-09-14"
    assert PIT_POLICY["next_open_role"] == "FUTURE_OUTCOME"
    assert "UNVERIFIED" in PIT_POLICY["previous_close_role"]


def test_inclusive_provider_end_is_clipped_and_raw_replay_is_required(phase1_fixture):
    cohort, calendar, _, make = phase1_fixture
    row = make()
    history = row["open"]["history"]
    page = history["pages"][0]
    raw = json.loads(page["body"])
    raw["bars"].append({**raw["bars"][0], "t": datetime.fromisoformat(history["end"]).isoformat()})
    page["body"] = json.dumps(raw)
    history["clipped_count"] = 1
    identity, histories = prepare_target(row, cohort, calendar)
    assert identity["status"] == "TARGET_AVAILABLE"
    assert len(histories["open"].candles) == 1
    # Changing normalized prices without the corresponding raw evidence must fail.
    history["candles"][0]["open"] = "100.5"
    with pytest.raises(NativeDataError, match="RAW_NORMALIZED_MISMATCH"):
        prepare_target(row, cohort, calendar)


def test_shared_gate_spaces_every_request_including_retries(monkeypatch):
    from sessionzero_database import dataset_fetch

    current = [100.0]
    starts = []
    monkeypatch.setattr(dataset_fetch.time, "monotonic", lambda: current[0])
    monkeypatch.setattr(
        dataset_fetch.time, "sleep", lambda delay: current.__setitem__(0, current[0] + delay)
    )
    gate = dataset_fetch.RequestGate()
    for _ in range(201):
        gate.wait()
        starts.append(current[0])
    assert starts[-1] - starts[0] >= 63.99


def test_private_archive_mode_checksum_and_safe_cli_errors(tmp_path, monkeypatch, capsys):
    from sessionzero_database import dataset_cli

    path = tmp_path / "private" / "data.json"
    write_json(path, {"test": True}, private=True)
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(NativeDataError, match="CHECKSUM"):
        check_archives({"archives": {"sha256": {"data.json": "0" * 64}}}, path.parent)
    secret = "synthetic-secret-must-not-leak"
    monkeypatch.setenv("ALPACA_SECRET_KEY", secret)
    monkeypatch.setattr("sys.argv", ["dataset"])

    def fail(**kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(dataset_cli, "build", fail)
    with pytest.raises(SystemExit):
        dataset_cli.main()
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "DATASET_CONFIGURATION_OR_STORAGE_FAILURE" in captured.out
