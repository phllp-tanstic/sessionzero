import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sessionzero_database.capture_cli import (
    CaptureProviderFailure,
    _native_close_retrieval,
    capture_iteration,
)
from sessionzero_database.outcome import _outcome_retrieval
from sessionzero_market_data import XnysTradingCalendar
from sessionzero_market_data.native import NativeCandle, NativeHistory, NativeInstrument, NativePage
from sessionzero_schemas import ProspectiveOutcomeRetrieval
from sessionzero_worker.main import _safe_log, derive_schedule, run_tick

CLI_PROCESS = (
    "import importlib, json, sys; "
    "worker = importlib.import_module('sessionzero_worker.main'); "
    "result = json.loads(sys.argv[1]); "
    "worker.run_tick = lambda: result; "
    "sys.argv = ['sessionzero-prospective-worker', 'tick']; "
    "worker.main()"
)


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_dst_safe_decision_timestamp_derivation():
    calendar = XnysTradingCalendar()
    dst = derive_schedule(utc("2026-03-09T12:20:00Z"), calendar)
    standard = derive_schedule(utc("2026-11-02T13:20:00Z"), calendar)
    assert dst.decision_timestamp == utc("2026-03-09T12:30:00Z")
    assert standard.decision_timestamp == utc("2026-11-02T13:30:00Z")
    assert dst.action == standard.action == "DECISION"


@pytest.mark.parametrize("timestamp", ["2026-07-03T12:20:00Z", "2026-09-20T12:20:00Z"])
def test_holiday_and_weekend_skip(timestamp):
    plan = derive_schedule(utc(timestamp), XnysTradingCalendar())
    assert plan.action == "SKIP"
    assert plan.reason == "NO_XNYS_SESSION"


def test_late_tick_never_derives_a_backfillable_decision_action():
    plan = derive_schedule(utc("2026-09-21T12:30:00.000001Z"), XnysTradingCalendar())
    assert plan.action == "WAIT_OUTCOME"
    assert plan.decision_timestamp == utc("2026-09-21T12:30:00Z")


@pytest.mark.parametrize(
    ("reason", "status"),
    [
        pytest.param("NO_XNYS_SESSION", "SKIPPED_NO_ACTION", id="holiday"),
        pytest.param("NO_XNYS_SESSION", "SKIPPED_NO_ACTION", id="weekend"),
        ("BEFORE_DECISION_WINDOW", "SKIPPED_NO_ACTION"),
        ("OUTCOME_NOT_YET_AVAILABLE", "SKIPPED_NO_ACTION"),
        ("NO_SNAPSHOT_AT_DECISION", "MISSED_DECISION_WINDOW"),
    ],
)
def test_no_action_tick_process_exits_cleanly(reason, status):
    result = {"status": status, "error_code": reason, "snapshot_version": None}
    completed = subprocess.run(
        [sys.executable, "-c", CLI_PROCESS, json.dumps(result)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == result


@pytest.mark.parametrize(
    "status",
    ["FAILED", "PARTIAL", "PROVIDER_UNAVAILABLE", "DATABASE_FAILURE", "IDENTITY_MISMATCH"],
)
def test_failed_tick_process_retains_nonzero_exit(status):
    result = {"status": status, "error_code": "TEST_FAILURE"}
    completed = subprocess.run(
        [sys.executable, "-c", CLI_PROCESS, json.dumps(result)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout) == result


def test_outcome_contract_requires_post_decision_event_and_request():
    decision = utc("2026-09-21T12:30:00Z")
    base = {
        "reality_symbol": "RAAPLUSDT",
        "native_ticker": "AAPL",
        "endpoint": "/bars",
        "decision_timestamp": decision,
        "event_time": utc("2026-09-21T13:30:00Z"),
        "request_time": utc("2026-09-21T13:47:00Z"),
        "ingestion_time": utc("2026-09-21T13:47:01Z"),
        "raw_response": {"test_only": True},
        "canonical_value": {"open": "100"},
        "git_commit": "a" * 40,
    }
    assert ProspectiveOutcomeRetrieval(**base).role == "FUTURE_OUTCOME"
    with pytest.raises(ValidationError, match="outcome event must follow"):
        ProspectiveOutcomeRetrieval(**{**base, "event_time": decision})
    with pytest.raises(ValidationError, match="request and ingestion must follow"):
        ProspectiveOutcomeRetrieval(
            **{**base, "request_time": decision, "ingestion_time": decision + timedelta(seconds=1)}
        )


def test_structured_logging_drops_unapproved_secret_fields(capsys):
    _safe_log(
        "test",
        status="FAILED",
        error_code="SAFE_CODE",
        database_url="postgresql://user:secret@example/db",
        alpaca_secret="secret-value",
    )
    output = capsys.readouterr().out
    assert "SAFE_CODE" in output
    assert "secret" not in output
    assert "postgresql" not in output


def test_database_failure_is_structured_and_does_not_require_process_state(monkeypatch):
    class FakeEngine:
        def dispose(self):
            pass

    monkeypatch.setattr(
        "sessionzero_worker.main.verify_database_connection",
        lambda engine: (_ for _ in ()).throw(RuntimeError("secret provider detail")),
    )
    result = run_tick(now=utc("2026-09-21T12:20:00Z"), engine=FakeEngine(), commit="a" * 40)
    assert result["status"] == "DATABASE_FAILURE"
    assert result["error_code"] == "DATABASE_UNAVAILABLE"


def test_canonical_capture_reports_completed_pairs_on_provider_failure(monkeypatch):
    class FakeBitget:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeAlpaca:
        def __init__(self, cohort):
            pass

        def close(self):
            pass

    completed = 0

    def reality(*args, **kwargs):
        nonlocal completed
        if completed == 4:
            raise RuntimeError("synthetic provider failure")
        completed += 1
        return object()

    monkeypatch.setattr(
        "sessionzero_database.capture_cli.validate_capture_window", lambda **kw: None
    )
    monkeypatch.setattr("sessionzero_database.capture_cli.git_commit", lambda: "a" * 40)
    monkeypatch.setattr("sessionzero_database.capture_cli.BitgetMarketClient", FakeBitget)
    monkeypatch.setattr("sessionzero_database.capture_cli.AlpacaNativeEquityProvider", FakeAlpaca)
    monkeypatch.setattr("sessionzero_database.capture_cli._reality_retrieval", reality)
    monkeypatch.setattr(
        "sessionzero_database.capture_cli._native_close_retrieval", lambda *a, **k: object()
    )
    with pytest.raises(CaptureProviderFailure) as failure:
        capture_iteration(
            decision_timestamp=utc("2026-09-21T12:30:00Z"),
            symbols=("RAAOIUSDT", "RAAPLUSDT", "RAMDUSDT", "RAMZNUSDT", "RASTSUSDT"),
        )
    assert failure.value.completed_symbols == 4


def test_outcome_adapter_uses_accepted_reality_mapping_and_first_minute():
    decision = utc("2026-09-18T12:30:00Z")
    opened = utc("2026-09-18T13:30:00Z")
    received = datetime.now(UTC)
    instrument = NativeInstrument(
        reality_symbol="RAAPLUSDT",
        native_ticker="AAPL",
        universe_version="u" * 64,
        cohort_version="c" * 64,
    )
    candle = NativeCandle(
        source="alpaca",
        native_ticker="AAPL",
        feed="sip",
        event_time=opened,
        ingestion_time=received,
        session_date=opened.date(),
        page_index=0,
        open=100,
        high=102,
        low=99,
        close=101,
        volume=10,
        trade_count=2,
    )
    page = NativePage(
        "/v2/stocks/AAPL/bars",
        {},
        received,
        {"x-request-id": "test-only"},
        json.dumps({"symbol": "AAPL", "bars": [{"t": opened.isoformat(), "o": 100}]}),
    )

    class Provider:
        def get_candles(self, symbol, start, end):
            assert (symbol, start, end) == ("RAAPLUSDT", opened, opened + timedelta(minutes=1))
            return NativeHistory(
                instrument,
                start,
                end,
                (replace(page, ingestion_time=datetime.now(UTC)),),
                (candle,),
                "alpaca",
            )

    outcome = _outcome_retrieval(
        Provider(),
        reality_symbol="RAAPLUSDT",
        decision_timestamp=decision,
        scheduled_open=opened,
        commit="a" * 40,
    )
    assert outcome.native_ticker == "AAPL"
    assert outcome.canonical_value == {"open": "100", "feed": "sip", "adjustment": "raw"}
    assert outcome.role == "FUTURE_OUTCOME"


def test_decision_close_adapter_reads_safe_response_headers():
    received = datetime.now(UTC)
    close_time = utc("2026-09-18T20:00:00Z")
    event = close_time - timedelta(minutes=1)
    instrument = NativeInstrument(
        reality_symbol="RAAPLUSDT",
        native_ticker="AAPL",
        universe_version="u" * 64,
        cohort_version="c" * 64,
    )
    candle = NativeCandle(
        source="alpaca",
        native_ticker="AAPL",
        feed="sip",
        event_time=event,
        ingestion_time=received,
        session_date=event.date(),
        page_index=0,
        open=100,
        high=102,
        low=99,
        close=101,
        volume=10,
        trade_count=2,
    )
    page = NativePage(
        "/v2/stocks/AAPL/bars",
        {},
        received,
        {"x-request-id": "test-only"},
        json.dumps({"symbol": "AAPL", "bars": [{"t": event.isoformat(), "c": 101}]}),
    )

    class Provider:
        def get_candles(self, symbol, start, end):
            assert (symbol, start, end) == ("RAAPLUSDT", event, close_time)
            return NativeHistory(
                instrument,
                start,
                end,
                (replace(page, ingestion_time=datetime.now(UTC)),),
                (candle,),
                "alpaca",
            )

    feature = _native_close_retrieval(
        Provider(), symbol="RAAPLUSDT", close_time=close_time, commit="a" * 40
    )
    assert feature.provider_identifiers == {"x-request-id": "test-only"}
    assert feature.field_name == "PREVIOUS_NATIVE_CLOSE"
