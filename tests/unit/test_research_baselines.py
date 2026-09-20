"""Synthetic prices ONLY in tests. No network or private archives required."""

import copy
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from research import baselines as b


@pytest.fixture
def protocol():
    return json.loads(b.PROTOCOL.read_text())


def session(open_time):
    return {"regular_open": open_time, "role": "EVALUATION"}


def test_frozen_dataset_and_calendar_identity():
    p, m, c = b.load_contract()
    assert p["dataset_version"] == m["dataset_version"]
    assert len(m["identity"]["members"]) == 21
    assert c["calendar_version"] == p["dataset_identity"]["calendar_version"]


def test_split_boundaries(protocol):
    dev = b.partition_bounds(protocol, "DEVELOPMENT")
    val = b.partition_bounds(protocol, "VALIDATION")
    assert dev[1] == val[0]
    assert val[1] == b.timestamp("2026-08-14T20:00:00Z")
    assert dev[1] - dev[0] == val[1] - val[0] == timedelta(days=30)
    assert b.in_partition(session("2026-07-15T13:30:00Z"), dev)
    assert not b.in_partition(session("2026-07-16T13:30:00Z"), dev)
    assert b.in_partition(session("2026-07-16T13:30:00Z"), val)
    assert not b.in_partition(session("2026-08-17T13:30:00Z"), val)


def test_purge_outcomes_crossing_boundary(protocol):
    bounds = b.partition_bounds(protocol, "DEVELOPMENT")
    assert not b.in_partition(session("2026-07-15T20:30:00Z"), bounds)
    assert not b.in_partition(session("2026-07-15T20:00:00Z"), bounds)
    assert not b.in_partition(session("2026-07-15T19:59:00Z"), bounds)


@pytest.mark.parametrize("partition", ["FINAL_OOS", "ALL", "final_oos", ""])
def test_oos_guard_before_any_archive_read(protocol, monkeypatch, partition):
    def forbidden(*args):
        pytest.fail("Archive read before guard")

    monkeypatch.setattr(b, "read_archive", forbidden)
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        b.evaluate(protocol, {}, {}, partition)


def test_overlapping_partition_rejected(protocol):
    protocol["splits"]["VALIDATION"][1] = "2026-08-15T20:00:00Z"
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        b.partition_bounds(protocol, "VALIDATION")


@pytest.mark.parametrize(
    "field",
    [
        "next_native_open",
        "previous_native_close",
        "reality_ohlcv",
        "corporate_actions",
        "unregistered_field",
        "future_or_incomplete_candles",
    ],
)
def test_unproven_and_future_fields_forbidden(protocol, field):
    t = b.timestamp("2026-07-01T12:30:00Z")
    with pytest.raises(ValueError, match="MODEL_FEATURE_FORBIDDEN"):
        b.require_model_eligible(protocol, field, t - timedelta(days=1), t)


def test_eligible_requires_availability_time(protocol):
    t = b.timestamp("2026-07-01T12:30:00Z")
    b.require_model_eligible(protocol, "calendar_schedule", t, t)
    for available in (None, t + timedelta(seconds=1)):
        with pytest.raises(ValueError):
            b.require_model_eligible(protocol, "calendar_schedule", available, t)


def test_decision_and_completed_bar_alignment():
    d = b.decision_time(session("2026-07-01T13:30:00Z"))
    assert d == b.timestamp("2026-07-01T12:30:00Z")
    c = d - timedelta(hours=16, minutes=30)
    bars = {d - timedelta(minutes=30): 103, d + timedelta(minutes=30): 999}
    assert b.select_mark(bars, d, c) == (103, 1800)
    assert b.select_mark({d: 999}, d, c) == (None, None)
    assert b.select_mark({c - timedelta(hours=1): 99}, d, c) == (None, None)


def test_baseline_formulas_and_missing():
    assert b.predict(100, 110, 100) == dict(zip(b.NAMES, [100, 110, 110, 105], strict=True))
    assert b.predict(100, 220, 200)["REALITY_RETURN_TRANSFER"] == 110
    assert b.predict(100, None, 100) == dict(zip(b.NAMES, [100, None, None, None], strict=True))
    assert b.predict(100, 110, None)["SIMPLE_BLEND"] is None
    for bad in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            b.predict(100, bad, 100)


def test_staleness_measured_not_tuned():
    d = b.timestamp("2026-07-01T12:30:00Z")
    c = d - timedelta(hours=16)
    assert b.select_mark({c: 100}, d, c) == (100, 57600)
    assert b.age_summary([1800, 1800, 7200]) == {
        "n": 3,
        "min_seconds": 1800,
        "median_seconds": 1800,
        "p95_seconds": 7200,
        "max_seconds": 7200,
        "over_one_hour": 1,
        "exclusion_threshold": None,
    }


def test_unknown_source_path_rejected():
    class Provider:
        def session_at(self, symbol, t):
            return SimpleNamespace(availability=SimpleNamespace(value="UNKNOWN"))

    t = b.timestamp("2026-07-01T12:30:00Z")
    assert not b.source_path_known(Provider(), "TEST", t - timedelta(hours=2), t)


def test_metrics_known_answer_and_ties():
    m = b.metrics([(102, 101, 100), (98, 100, 100)])
    assert m["price"] == {
        "mae": 1.5,
        "rmse": pytest.approx(2.5**0.5),
        "median_absolute_error": 1.5,
        "signed_bias": -0.5,
    }
    assert m["bps"]["mae"] == 150
    assert m["directional_accuracy"] == 0.5
    assert b.metrics([(100, 101, 100)])["directional_accuracy"] == 0
    assert b.metrics([(100, 100, 100)])["directional_accuracy"] == 1
    assert b.metrics([])["price"] is None


def test_experiment_identity(protocol):
    first = b.experiment_identity(protocol, {"code": "a"}, "DEVELOPMENT")
    assert b.digest(first) == b.digest(
        b.experiment_identity(protocol, {"code": "a"}, "DEVELOPMENT")
    )
    assert b.digest(first) != b.digest(
        b.experiment_identity(protocol, {"code": "b"}, "DEVELOPMENT")
    )
    changed = copy.deepcopy(protocol)
    changed["parameters"]["blend_weight"] = 0.7
    assert b.digest(first) != b.digest(b.experiment_identity(changed, {"code": "a"}, "DEVELOPMENT"))


def test_no_outcome_argument_and_no_global_target_state():
    before = b.predict(100, 102, 101)
    outcomes = [1, 999999]
    for outcome in outcomes:
        b.metrics([(before["PREVIOUS_CLOSE"], outcome, 100)])
        assert b.predict(100, 102, 101) == before
    with pytest.raises(TypeError):
        b.predict(100, 102, 101, next_native_open=999)


def test_missing_native_exact_boundary():
    t = b.timestamp("2026-07-01T13:30:00Z")
    assert b.native_price(None, "open", t) is None
    assert b.native_price({"open": {"status": "MISSING_BOUNDARY_MINUTE"}}, "open", t) is None
    with pytest.raises(ValueError, match="exact native boundary"):
        b.native_price(
            {
                "open": {
                    "status": "AVAILABLE",
                    "history": {"candles": [{"event_time": "2026-07-01T13:31:00Z", "open": "100"}]},
                }
            },
            "open",
            t,
        )


def test_pipeline_outcome_and_oos_isolation(protocol, phase1_fixture, monkeypatch):
    cohort, calendar, _, make_row = phase1_fixture
    previous, current = calendar["sessions"][:2]
    holdout = next(s for s in calendar["sessions"] if s["session_date"] == "2026-08-17")
    mini_calendar = {"sessions": [previous, current, holdout]}
    member = cohort.members[0]
    manifest = {"identity": {"members": [{"symbol": member.symbol}]}}
    native_rows = [make_row(previous), make_row(current), {"session": holdout}]
    # Holdout intentionally has NO price legs: any access will fail.
    close = b.timestamp(previous["regular_close"])
    decision = b.decision_time(current)
    observations = [
        {"candle": {"event_time": (t - timedelta(hours=1)).isoformat(), "close": "102"}}
        for t in [close, decision - timedelta(minutes=30)]
    ]

    def archive(_, filename):
        if filename.startswith("native"):
            return {"rows": native_rows}
        return {"observations": observations}

    monkeypatch.setattr(b, "read_archive", archive)
    first = b.evaluate(protocol, manifest, mini_calendar, "DEVELOPMENT")
    assert first["candidate_observations"] == 1
    assert first["metrics"]["SIMPLE_BLEND"]["n"] == 1
    native_rows[1]["open"]["history"]["candles"][0]["open"] = "99999"
    # Same-session native close is also in the future at decision time.
    native_rows[1]["close"]["history"]["candles"][0]["close"] = "77777"
    observations.append({"candle": {"event_time": decision.isoformat(), "close": "88888"}})
    second = b.evaluate(protocol, manifest, mini_calendar, "DEVELOPMENT")
    assert first["records"][0]["predictions"] == second["records"][0]["predictions"]
    assert first["metrics"] != second["metrics"]


def test_future_publication_cannot_prove_source_availability():
    t = b.timestamp("2026-07-01T12:30:00Z")

    class Provider:
        evidence = (SimpleNamespace(evidence_id="future", publication_time=t + timedelta(days=1)),)

        def session_at(self, symbol, at):
            return SimpleNamespace(
                availability=SimpleNamespace(value="EXPECTED_OPEN"), evidence_ids=["future"]
            )

    assert not b.source_path_known(Provider(), "TEST", t - timedelta(hours=2), t)


def test_protocol_mutation_fails_closed(tmp_path, monkeypatch, protocol):
    protocol["splits"]["FINAL_OOS"][0] = "2026-09-01T00:00:00Z"
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    monkeypatch.setattr(b, "PROTOCOL", path)
    with pytest.raises(ValueError, match="Frozen protocol changed"):
        b.load_contract()
