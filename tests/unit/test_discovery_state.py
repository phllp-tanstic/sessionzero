"""Synthetic-only state research checks; no final-holdout observations."""

import copy

import pytest

from research import baselines as b
from research import discovery_state as ds
from research import fair_value as fv
from research import fair_value_v2 as v2


def sample(day, mark=102, outcome=102, symbol="A"):
    return {
        "symbol": symbol,
        "decision_timestamp": f"2026-07-{day:02d}T12:30:00+00:00",
        "previous_native_close": 100.0,
        "baselines": {"REALITY_MARK": mark},
        "outcome": outcome,
        "features": {
            "momentum_3h": 0.01,
            "range": 0.02,
            "reversal": -0.001,
            "path_efficiency": 0.8,
            "sign_changes": 0.2,
            "native_day": None,
            "prior_gap": None,
            "mark_age_hours": 0.5,
            "missing_fraction": 0.0,
            "observation_count": 10,
            "prior_gap_missing": 1.0,
        },
        "input_refs": {"historical_availability": "UNKNOWN_AVAILABILITY"},
    }


def test_exact_state_rules_direction_and_determinism():
    policy = ds.load_protocol()[0]["label_policy"]
    cases = [
        (102, 102, "DISCOVERY"),
        (102, 104, "UNDERREACTION"),
        (104, 102, "OVERSHOOT"),
        (102, 99, "NOISE"),
        (100.1, 101, "NOISE"),
        (102, 100.1, "NOISE"),
        (98, 96, "UNDERREACTION"),
    ]
    for mark, outcome, expected in cases:
        assert ds.state_label(sample(1, mark, outcome), 0.002, policy) == expected
        assert ds.state_label(sample(1, mark, outcome), 0.002, policy) == expected


def test_fit_only_floor_version_and_identity():
    protocol, _, _ = ds.load_protocol()
    assert protocol["state_label_version"] == "discovery_label_ratio.v1"
    train = [sample(i, 100 + i / 10) for i in range(1, 11)]
    floor = ds.label_scale(train, protocol["label_policy"])
    changed = copy.deepcopy(train)
    for r in changed:
        r["outcome"] = 9999
    assert ds.label_scale(changed, protocol["label_policy"]) == floor
    assert floor > 0


def test_features_ignore_future_outcome_and_confidence_is_deterministic():
    p = ds.load_protocol()[0]
    rows = [sample(day, 100 + day / 5, 100 + day / 4) for day in range(1, 25)]
    x = sample(25, 103, 105, "UNSEEN")
    before = ds.features(x)
    x["outcome"] = 100000
    assert ds.features(x) == before
    names = p["groups"]["D"]
    labels = [
        ds.state_label(r, ds.label_scale(rows, p["label_policy"]), p["label_policy"]) for r in rows
    ]
    m = ds.Logit(names, p["states"], p["model_parameters"]).fit(rows, labels)
    probs = m.probabilities([x])[0]
    assert 0 <= max(probs) <= 1 and sum(probs) == pytest.approx(1)
    assert (
        probs.tolist()
        == ds.Logit(names, p["states"], p["model_parameters"])
        .fit(rows, labels)
        .probabilities([x])[0]
        .tolist()
    )
    assert ds.calibration_temperature(
        rows, p["label_policy"], names, p
    ) == ds.calibration_temperature(rows, p["label_policy"], names, p)


def test_confusion_and_bucket_calculations():
    m = ds.metrics([("NOISE", "NOISE"), ("NOISE", "DISCOVERY")], ["DISCOVERY", "NOISE"])
    assert m["per_class"]["NOISE"]["recall"] == 0.5
    assert m["balanced_accuracy"] == 0.25


def test_chronology_and_oos_guard_before_archive(monkeypatch):
    protocol, manifest, calendar = ds.load_protocol()
    assert protocol["folds"] == v2.load_protocol()[0]["folds"]
    monkeypatch.setattr(b, "read_archive", lambda *_: pytest.fail("archive read"))
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        fv.rows_for_bounds(
            manifest,
            calendar,
            (b.timestamp("2026-06-15T20:00:00Z"), b.timestamp("2026-08-15T20:00:00Z")),
        )


def test_state_record_excludes_outcome():
    p = ds.load_protocol()[0]
    rows = [
        sample(day, 100 + day / 5, 100 + day / 4, symbol=s)
        for day in range(1, 26)
        for s in ("A", "B", "C", "D", "E", "F", "G")
    ]
    result, records = ds.evaluate(rows, p)
    assert result["scored_rows"] == len(records) == 70
    assert all("outcome" not in r and "next_open" not in r and "pnl" not in r for r in records)
    assert all(0 <= r["discovery_confidence"] <= 1 for r in records)


def test_only_completed_trailing_candles_eligible():
    close = b.timestamp("2026-07-01T20:00:00Z")
    decision = b.timestamp("2026-07-02T12:30:00Z")
    bars = [
        {"candle": {"event_time": "2026-07-01T19:00:00Z", "close": "100"}},
        {"candle": {"event_time": "2026-07-02T11:00:00Z", "close": "101"}},
        {"candle": {"event_time": "2026-07-02T12:00:00Z", "close": "999"}},
    ]
    selected = fv.eligible_candles(bars, close, decision)
    assert len(selected) == 2
    assert all(t < decision for t in selected)
