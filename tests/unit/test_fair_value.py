"""Synthetic examples only; no private prices or providers."""

import copy
from datetime import timedelta

import pytest

from research import baselines as b
from research import fair_value as fv


def t(value):
    return b.timestamp(value)


def candle(completion, close=102, high=103, low=100, open_price=101):
    return {
        "candle": {
            "event_time": (completion - timedelta(hours=1)).isoformat(),
            "open": str(open_price),
            "high": str(high),
            "low": str(low),
            "close": str(close),
        }
    }


def row(day, symbol="TEST", result=102, **features):
    return {
        "symbol": symbol,
        "decision_timestamp": f"2026-06-{day:02d}T12:30:00+00:00",
        "previous_native_close": 100,
        "outcome": result,
        "features": {name: features.get(name, 0.01) for name in fv.GROUPS["FULL"]},
        "input_refs": {"historical_availability": "UNKNOWN_AVAILABILITY"},
        "baselines": b.predict(100, 101, 100),
    }


def test_completed_trailing_candles_and_future_rejection():
    close, decision = t("2026-06-20T20:00:00Z"), t("2026-06-21T12:30:00Z")
    archive = [candle(close, 100), candle(decision - timedelta(minutes=30)), candle(decision, 999)]
    eligible = fv.eligible_candles(archive, close, decision)
    assert len(eligible) == 2
    assert max(eligible) < decision
    features, refs = fv.feature_vector(eligible, close, decision, 100, 99, 98)
    assert features["displacement"] == pytest.approx(0.02)
    assert refs["reality_latest_completion"] != decision.isoformat()
    with pytest.raises(ValueError, match="Future"):
        fv.feature_vector({decision: archive[-1]["candle"]}, close, decision, 100, 99, 98)
    assert fv.feature_vector({}, close, decision, 100, 99, 98) is None


def test_development_scaler_and_missing_policy():
    training = [row(16, displacement=0, prior_gap=None), row(17, displacement=0.02, prior_gap=0.01)]
    holdout = row(18, displacement=500, prior_gap=None)
    model = fv.LinearModel(fv.GROUPS["FULL"], False).fit(training)
    assert model.mean[0] == pytest.approx(0.01)
    assert model.mean[5] == pytest.approx(0.01)
    prediction = model.predict([holdout])[0]
    assert prediction == pytest.approx(model.predict([holdout])[0])
    assert model.mean[0] == pytest.approx(0.01)


def test_internal_split_is_date_blocked():
    observations = [row(day, symbol=s) for day in range(16, 21) for s in ("A", "B")]
    train, holdout = fv.internal_split(observations)
    assert max(r["decision_timestamp"] for r in train) < min(
        r["decision_timestamp"] for r in holdout
    )
    assert len(train) == 6


def test_prediction_contract_and_common_alignment():
    rows = [row(16), row(17)]
    rows[1]["baselines"]["SIMPLE_BLEND"] = None
    prediction = fv.prediction_record(rows[0], 101.5, "RIDGE_PATH", "VALIDATION")
    assert prediction["predicted_reopen_return"] == pytest.approx(0.015)
    assert prediction["fair_value_price"] == pytest.approx(101.5)
    assert "outcome" not in prediction and "target" not in prediction
    other = fv.prediction_record(rows[1], 103, "RIDGE_PATH", "VALIDATION")
    comparison = fv.comparisons(rows, [prediction, other])
    assert comparison["common_count"] == 1
    assert comparison["metrics"]["FAIR_VALUE"]["candidate"]["n"] == 2
    assert comparison["metrics"]["FAIR_VALUE"]["common"]["n"] == 1


def test_ablations_selection_development_only_and_no_mutation():
    assert tuple(fv.GROUPS) == ("DISPLACEMENT", "PATH", "NATIVE", "FULL")
    dev = [row(day, symbol=s, result=100 + day / 10) for day in range(16, 26) for s in ("A", "B")]
    val = [row(day, result=101) for day in range(26, 29)]
    original = copy.deepcopy(dev)
    result, choice, predictions = fv.evaluate_models(dev, val)
    assert len(result) == 8
    assert len(predictions) == len(dev) + len(val)
    val[0]["outcome"] = 100000
    changed, selection, _ = fv.evaluate_models(dev, val)
    assert selection == choice
    assert changed[choice["selected"]]["validation"] != result[choice["selected"]]["validation"]
    assert dev == original


@pytest.mark.parametrize("partition", ["FINAL_OOS", "ALL", "final_oos"])
def test_guard_before_archive_read(partition, monkeypatch):
    protocol, _, calendar = b.load_contract()
    monkeypatch.setattr(b, "read_archive", lambda *_: pytest.fail("Archive read"))
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        fv.rows_for_partition(protocol, {}, calendar, partition)


def test_claim_and_identity():
    assert fv.CLAIM == "RETROSPECTIVE ESTIMATED"
    assert "OOS" not in fv.GROUPS
    assert b.digest({"model": fv.VERSION, "parameters": fv.PARAMETERS}) == b.digest(
        {"model": fv.VERSION, "parameters": fv.PARAMETERS}
    )
    assert b.digest({"model": fv.VERSION}) != b.digest({"model": "changed"})


def test_pipeline_keeps_future_open_out_of_prediction(phase1_fixture, monkeypatch):
    cohort, calendar, _, make_row = phase1_fixture
    previous, current = calendar["sessions"][:2]
    holdout = next(s for s in calendar["sessions"] if s["session_date"] == "2026-08-17")
    mini = {"sessions": [previous, current, holdout]}
    member = cohort.members[0]
    manifest = {"identity": {"members": [{"symbol": member.symbol}]}}
    native = [make_row(previous), make_row(current), {"session": holdout}]
    close = b.timestamp(previous["regular_close"])
    decision = b.decision_time(current)
    observations = [
        candle(close, 100),
        candle(decision - timedelta(minutes=30), 102),
        candle(decision, 999),
    ]
    monkeypatch.setattr(
        b,
        "read_archive",
        lambda _manifest, filename: (
            {"rows": native} if filename.startswith("native") else {"observations": observations}
        ),
    )
    monkeypatch.setattr(fv.b, "source_path_known", lambda *_: True)
    protocol, _, _ = b.load_contract()
    first = fv.rows_for_partition(protocol, manifest, mini, "DEVELOPMENT")
    assert len(first) == 1
    native[1]["open"]["history"]["candles"][0]["open"] = "99999"
    native[1]["close"]["history"]["candles"][0]["close"] = "77777"
    later = fv.rows_for_partition(protocol, manifest, mini, "DEVELOPMENT")
    assert first[0]["features"] == later[0]["features"]
    assert first[0]["input_refs"] == later[0]["input_refs"]
    assert first[0]["outcome"] != later[0]["outcome"]
