"""Synthetic pre-OOS examples; no provider values or final-holdout outcomes."""

import copy
import json

import pytest

from research import baselines as b
from research import fair_value_v2 as v2


def sample(day, symbol="A", outcome=102, displacement=0.01):
    decision = f"2026-07-{day:02d}T12:30:00+00:00"
    return {
        "symbol": symbol,
        "decision_timestamp": decision,
        "previous_native_close": 100.0,
        "outcome": outcome,
        "features": {"displacement": displacement, "range": 0.015, "native_day": 0.01},
        "baselines": {"REALITY_MARK": 101.0, "REALITY_RETURN_TRANSFER": 100 * (1 + displacement)},
        "input_refs": {"historical_availability": "UNKNOWN_AVAILABILITY"},
    }


def test_protocol_transition_and_boundaries():
    protocol, _, _ = v2.load_protocol()
    assert protocol["historical_partitions"]["VALIDATION"] == [
        "2026-07-15T20:00:00Z",
        "2026-08-14T20:00:00Z",
    ]
    assert v2.research_bounds(protocol)[1] == b.timestamp("2026-08-14T20:00:00Z")
    altered = copy.deepcopy(protocol)
    altered["splits"]["PRE_OOS_RESEARCH"][1] = "2026-08-15T20:00:00Z"
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        v2.research_bounds(altered)
    assert (
        b.partition_bounds(b.load_contract()[0], "VALIDATION")[1] == v2.research_bounds(protocol)[1]
    )


def test_guard_precedes_archive_read(monkeypatch):
    protocol, manifest, calendar = v2.load_protocol()
    monkeypatch.setattr(b, "read_archive", lambda *_: pytest.fail("archive accessed"))
    with pytest.raises(ValueError, match="FINAL_OOS_LOCKED"):
        v2.v1.rows_for_bounds(
            manifest,
            calendar,
            (v2.research_bounds(protocol)[0], b.timestamp("2026-08-15T20:00:00Z")),
        )


def test_folds_are_blocked_and_fit_labels_precede_prediction():
    protocol, _, _ = v2.load_protocol()
    rows = [
        sample(day, symbol=s) for day in range(1, 26) for s in ("A", "B", "C", "D", "E", "F", "G")
    ]
    seen = []
    for train, test, definition in v2.folds(rows, protocol):
        assert max(r["decision_timestamp"] for r in train) < min(
            r["decision_timestamp"] for r in test
        )
        assert b.timestamp(definition["latest_fit_outcome_completion"]) < b.timestamp(
            test[0]["decision_timestamp"]
        )
        seen.extend((r["symbol"], r["decision_timestamp"]) for r in test)
    assert len(seen) == len(set(seen)) == 70


def test_no_future_target_or_symbol_specific_fit():
    params = v2.load_protocol()[0]["parameters"]
    train = [
        sample(i, symbol="A" if i % 2 else "B", outcome=100 + i / 4, displacement=i / 1000)
        for i in range(1, 10)
    ]
    future = sample(20, symbol="UNSEEN", outcome=104, displacement=0.03)
    for kind in ("SHRUNK_TRANSFER", "ROBUST_TRANSFER", "PIECEWISE_TRANSFER"):
        model = v2.TransferModel(kind, params).fit(train)
        before = model.predict_return(future)
        future["outcome"] = 1000000
        assert model.predict_return(future) == before
        assert len(model.coef) <= 3
        assert (
            model.parameters_record()
            == v2.TransferModel(kind, params).fit(train).parameters_record()
        )
    assert v2.design(future, "PIECEWISE_TRANSFER", 0.02) == pytest.approx([0.03, 0.01])
    assert v2.design(sample(20, displacement=-0.03), "PIECEWISE_TRANSFER", 0.02) == pytest.approx(
        [-0.03, -0.01]
    )


def test_regularization_and_unseen_symbol_pooled_fallback():
    params = v2.load_protocol()[0]["parameters"]
    train = [sample(i, outcome=100 + 100 * i / 100, displacement=i / 100) for i in range(1, 12)]
    regular = v2.TransferModel("SHRUNK_TRANSFER", params).fit(train)
    unregularized = v2.TransferModel("SHRUNK_TRANSFER", {**params, "ridge_alpha": 0}).fit(train)
    assert abs(regular.coef[1]) < abs(unregularized.coef[1])
    unknown = sample(20, symbol="UNSEEN", displacement=0.04)
    known = sample(20, symbol="A", displacement=0.04)
    assert regular.predict_return(unknown) == regular.predict_return(known)


def test_reproducible_outcome_free_predictions():
    protocol, _, _ = v2.load_protocol()
    rows = [
        sample(day, symbol=s, outcome=100 + day / 4, displacement=day / 1000)
        for day in range(1, 26)
        for s in ("A", "B", "C", "D", "E", "F", "G")
    ]
    first, ledger = v2.evaluate(rows, protocol)
    second, repeat = v2.evaluate(rows, protocol)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert ledger == repeat
    assert all("outcome" not in r and "target" not in r for r in ledger)
    assert first["scored_rows"] == 70
    assert len(ledger) == first["scored_rows"] * 4
    # Target mutation in the prediction block cannot affect any fitted coefficient or forecast.
    changed = copy.deepcopy(rows)
    for r in changed:
        if r["decision_timestamp"] >= "2026-07-16":
            r["outcome"] = 99999
    _, modified = v2.evaluate(changed, protocol)
    assert [r for r in ledger if r["fold"] == 0] == [r for r in modified if r["fold"] == 0]


def test_cross_sectional_timing_not_used():
    protocol, _, _ = v2.load_protocol()
    assert "cross_sectional" not in protocol["feature_set_version"]
    assert protocol["candidates"] == [
        "REALITY_MARK",
        "SHRUNK_TRANSFER",
        "ROBUST_TRANSFER",
        "PIECEWISE_TRANSFER",
    ]
    assert v2.CLAIM == "RETROSPECTIVE ESTIMATED"
