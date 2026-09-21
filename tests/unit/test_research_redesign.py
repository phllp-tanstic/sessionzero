"""Synthetic-only trajectory audit tests; no provider calls or holdout rows."""

import copy
from datetime import timedelta

import pytest

from research import baselines as b
from research import research_redesign as rr


def protocol():
    return rr.protocol_and_inputs()[0]


def test_calendar_relative_grid_and_hourly_redundancy():
    close = b.timestamp("2026-07-01T20:00:00Z")
    opening = b.timestamp("2026-07-02T13:30:00Z")
    points = rr.grid(close, opening, protocol()["slots"])
    assert [name for name, _ in points] == [x["name"] for x in protocol()["slots"]]
    assert dict(points)["CLOSE_PLUS_2H"] == close + timedelta(hours=2)
    assert dict(points)["OPEN_MINUS_1H"] == opening - timedelta(hours=1)
    assert dict(points)["OPEN_MINUS_30M"] == opening - timedelta(minutes=30)
    with pytest.raises(ValueError, match="Duplicate"):
        rr.grid(close, opening, [protocol()["slots"][0], protocol()["slots"][0]])
    winter_close = b.timestamp("2026-12-01T21:00:00Z")
    winter_open = b.timestamp("2026-12-02T14:30:00Z")
    winter = dict(rr.grid(winter_close, winter_open, protocol()["slots"]))
    assert winter["OPEN_MINUS_1H"] == b.timestamp("2026-12-02T13:30:00Z")
    assert winter["CLOSE_PLUS_2H"] == b.timestamp("2026-12-01T23:00:00Z")


def test_strictly_trailing_features_and_no_outcome_parameter():
    close = b.timestamp("2026-07-01T20:00:00Z")
    evaluation = close + timedelta(hours=3, minutes=30)
    anchor = {"open": "100", "high": "100", "low": "99", "close": "100"}
    second = {"open": "100", "high": "102", "low": "100", "close": "101"}
    candles = {close: anchor, close + timedelta(hours=2): second}
    f = rr.path_features(candles, close, evaluation, 100)
    assert f["mark"] == 101
    assert f["observation_count"] == 2
    assert f["staleness_hours"] == 1.5
    future = {**candles, evaluation: {"open": "1", "high": "1", "low": "1", "close": "1"}}
    with pytest.raises(ValueError, match="Future"):
        rr.path_features(future, close, evaluation, 100)
    with pytest.raises(ValueError, match="anchor"):
        rr.path_features({close + timedelta(hours=2): second}, close, evaluation, 100)


def test_label_sensitivity_is_deterministic():
    p = protocol()["label_policy"]
    assert (
        rr.label(0.02, 0.02, 0.001, p["reference_ratio_lower"], p["reference_ratio_upper"])
        == "DISCOVERY"
    )
    assert (
        rr.label(0.02, 0.028, 0.001, p["reference_ratio_lower"], p["reference_ratio_upper"])
        == "DISCOVERY"
    )
    assert (
        rr.label(0.02, 0.028, 0.001, p["alternative_ratio_lower"], p["alternative_ratio_upper"])
        == "UNDERREACTION"
    )
    assert (
        rr.label(0.02, -0.01, 0.001, p["reference_ratio_lower"], p["reference_ratio_upper"])
        == "NOISE"
    )


def test_transition_matrix_exact_counts_and_persistence():
    result = rr.transition_matrix([["NOISE", "DISCOVERY", "OVERSHOOT"], ["NOISE", "NOISE"]])
    assert result["counts"]["NOISE"]["DISCOVERY"] == 1
    assert result["counts"]["NOISE"]["NOISE"] == 1
    assert result["counts"]["DISCOVERY"]["OVERSHOOT"] == 1
    assert result["conditional_probability"]["NOISE"]["DISCOVERY"] == 0.5
    assert result["persistence"] == pytest.approx(1 / 3)


def test_timestamp_specific_counts_and_outcome_separation():
    p = copy.deepcopy(protocol())
    p["slots"] = p["slots"][:2]
    p["label_policy"]["resolution_fit_sessions"] = 2
    records, evaluations = [], []
    for day in range(1, 5):
        for slot in p["slots"]:
            records.append(
                {
                    "symbol": "TEST",
                    "cash_session_date": f"2026-07-{day:02d}",
                    "evaluation_timestamp": f"2026-07-{day:02d}T12:00:00+00:00",
                    "slot": slot["name"],
                    "trajectory_features": {
                        "reality_displacement": 0.01 * day,
                        "realized_volatility": 0.02,
                        "path_efficiency": 0.5,
                        "reversal_magnitude": 0.01,
                    },
                }
            )
            evaluations.append(
                {"record_index": len(records) - 1, "outcome": 101 + day, "previous_close": 100}
            )
    before = copy.deepcopy(records)
    result = rr.analyze(p, records, evaluations, {"candidate_cash_sessions": 4})
    assert records == before
    assert result["outcome_joined_rows"] == 8
    assert all(
        sum(result["state_counts_by_slot"][s].values()) == 4 for s in result["state_counts_by_slot"]
    )


def test_final_oos_guard_precedes_archive(monkeypatch):
    p, manifest, calendar = rr.protocol_and_inputs()
    p = copy.deepcopy(p)
    p["split"][1] = "2026-08-15T20:00:00Z"
    monkeypatch.setattr(b, "read_archive", lambda *_: pytest.fail("archive read"))
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        rr.extract(p, manifest, calendar)


def test_capability_and_capture_gap_determinism():
    assert rr.source_audit() == rr.source_audit()
    assert rr.source_audit()["ALPACA_BOATS"]["status"] == "GATED"
    current = {"REALITY_DECISION_MARK", "PREVIOUS_NATIVE_CLOSE", "LATER_OUTCOME_VERSION_LINK"}
    gaps = rr.capture_gaps(current)
    assert "RAW_REALITY_PATH_OHLCV" in gaps
    assert gaps == rr.capture_gaps(current)
    assert not rr.capture_gaps(current | set(gaps))


def test_confidence_target_calculation():
    rows = [
        {"residual_bps": -20, "direction_agreement": True, "state": "DISCOVERY"},
        {"residual_bps": 40, "direction_agreement": False, "state": "OVERSHOOT"},
    ]
    summary = rr.summarize(rows)
    assert summary["mark_mae_bps"] == 30
    assert summary["direction_agreement"] == 0.5
    assert summary["overshoot_rate"] == 0.5
