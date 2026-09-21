"""Private retrospective Discovery State diagnostic; final OOS is unsupported."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

import numpy as np
from sessionzero_database.dataset_artifacts import digest

from research import baselines as b
from research import fair_value as fv
from research import fair_value_v2 as v2

CONTRACT = b.ROOT / "research/protocols/discovery-state-v1.json"
CLAIM = "RETROSPECTIVE ESTIMATED"


def load_protocol() -> tuple[dict, dict, dict]:
    parent, manifest, calendar = v2.load_protocol()
    v2.research_bounds(parent)  # fail closed before archive access
    protocol = json.loads(CONTRACT.read_text())
    if (
        protocol["parent_protocol_version"] != parent["protocol_version"]
        or protocol["dataset_version"] != parent["dataset_version"]
        or protocol["folds"] != parent["folds"]
        or protocol["states"] != ["DISCOVERY", "UNDERREACTION", "OVERSHOOT", "NOISE"]
        or protocol["fair_value_reference_version"] != "FAIR_VALUE_BASELINE_V0"
    ):
        raise ValueError("Discovery protocol identity changed")
    return protocol, manifest, calendar


def label_scale(training: list[dict], policy: dict) -> float:
    """Fit-only resolution floor; zero-movement training cannot define labels."""
    median = float(np.median([abs(reality_return(r)) for r in training]))
    if median <= 0:
        raise ValueError("No fit-only displacement scale")
    return median * policy["noise_floor_fraction_of_training_median_absolute_reality_return"]


def reality_return(row: dict) -> float:
    return row["baselines"]["REALITY_MARK"] / row["previous_native_close"] - 1


def state_label(row: dict, floor: float, policy: dict) -> str:
    if floor <= 0:
        raise ValueError("Invalid label resolution")
    r = reality_return(row)
    o = row["outcome"] / row["previous_native_close"] - 1
    if abs(r) <= floor or abs(o) <= floor or r * o <= 0:
        return "NOISE"
    ratio = o / r
    if ratio < policy["agreement_ratio_lower"]:
        return "OVERSHOOT"
    if ratio > policy["agreement_ratio_upper"]:
        return "UNDERREACTION"
    return "DISCOVERY"


def features(row: dict) -> dict:
    """Outcome is deliberately not accessed; all path inputs were completed before T."""
    f = row["features"]
    return {
        "reality_return": reality_return(row),
        "absolute_displacement": abs(reality_return(row)),
        "momentum_3h": f["momentum_3h"],
        "range": f["range"],
        "reversal": f["reversal"],
        "path_efficiency": f["path_efficiency"],
        "sign_changes": f["sign_changes"],
        "native_day": f["native_day"],
        "prior_gap": f["prior_gap"],
        "mark_age_hours": f["mark_age_hours"],
        "missing_fraction": f["missing_fraction"],
        "observation_count": f["observation_count"],
        "prior_gap_missing": f["prior_gap_missing"],
    }


def add_path_features(rows: list[dict], manifest: dict, calendar: dict) -> None:
    """Read only trailing hourly bars; the Fair Value row builder already gates OOS."""
    from datetime import timedelta

    sessions = {s["session_date"]: s for s in calendar["sessions"]}
    by_symbol = defaultdict(list)
    for row in rows:
        by_symbol[row["symbol"]].append(row)
    for symbol, subset in by_symbol.items():
        observations = b.read_archive(manifest, f"reality-{symbol}.json")["observations"]
        for row in subset:
            decision = b.timestamp(row["decision_timestamp"])
            previous = max(
                (s for s in sessions.values() if b.timestamp(s["regular_close"]) < decision),
                key=lambda s: s["regular_close"],
            )
            close = b.timestamp(previous["regular_close"])
            candles = fv.eligible_candles(observations, close, decision)
            if (
                digest([candles[t] for t in sorted(candles)])
                != row["input_refs"]["reality_input_hash"]
            ):
                raise ValueError("Trailing path provenance mismatch")
            if any(t >= decision or t < close for t in candles):
                raise ValueError("Future candle")
            times = sorted(candles)
            closes = [float(candles[t]["close"]) for t in times]
            steps = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
            travel = sum(abs(x) for x in steps)
            row["features"].update(
                path_efficiency=abs(closes[-1] - closes[0]) / travel if travel else 0.0,
                sign_changes=sum(a * c < 0 for a, c in pairwise(steps)) / max(1, len(steps) - 1),
                observation_count=len(times),
            )
            assert all(t + timedelta(0) < decision for t in times)


class Logit:
    """Deterministic pooled L2 softmax with fit-only standardization and mean imputation."""

    def __init__(self, names: list[str], states: list[str], parameters: dict):
        self.names, self.states, self.parameters = names, states, parameters

    def matrix(self, rows: list[dict], fit: bool = False) -> np.ndarray:
        x = np.asarray(
            [
                [np.nan if features(r)[n] is None else features(r)[n] for n in self.names]
                for r in rows
            ],
            dtype=float,
        )
        if fit:
            self.mean = np.array([np.nanmean(col) if np.isfinite(col).any() else 0 for col in x.T])
        x = np.where(np.isfinite(x), x, self.mean)
        if fit:
            self.scale = np.where(x.std(axis=0) > 1e-12, x.std(axis=0), 1)
        return np.column_stack((np.ones(len(x)), (x - self.mean) / self.scale))

    def fit(self, rows: list[dict], labels: list[str]) -> Logit:
        x = self.matrix(rows, fit=True)
        y = np.asarray([self.states.index(s) for s in labels])
        self.weights = np.zeros((x.shape[1], len(self.states)))
        p = self.parameters
        for _ in range(p["steps"]):
            z = x @ self.weights
            z -= z.max(axis=1, keepdims=True)
            probs = np.exp(z)
            probs /= probs.sum(axis=1, keepdims=True)
            probs[np.arange(len(y)), y] -= 1
            gradient = x.T @ probs / len(y)
            gradient[1:] += p["l2"] * self.weights[1:] / len(y)
            self.weights -= p["learning_rate"] * gradient
        return self

    def probabilities(self, rows: list[dict], temperature: float = 1.0) -> np.ndarray:
        z = self.matrix(rows) @ self.weights / temperature
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z)
        return p / p.sum(axis=1, keepdims=True)


def calibration_temperature(
    train: list[dict], policy: dict, names: list[str], protocol: dict
) -> float:
    dates = sorted({r["decision_timestamp"] for r in train})
    cut = max(1, int(len(dates) * protocol["model_parameters"]["calibration_train_fraction"]))
    early = [r for r in train if r["decision_timestamp"] < dates[cut]]
    later = [r for r in train if r["decision_timestamp"] >= dates[cut]]
    if not early or not later:
        raise ValueError("Insufficient calibration dates")
    floor = label_scale(early, policy)
    model = Logit(names, protocol["states"], protocol["model_parameters"]).fit(
        early, [state_label(r, floor, policy) for r in early]
    )
    labels = np.asarray([protocol["states"].index(state_label(r, floor, policy)) for r in later])
    return min(
        protocol["model_parameters"]["temperatures"],
        key=lambda t: (
            -np.log(
                np.maximum(model.probabilities(later, t)[np.arange(len(later)), labels], 1e-12)
            ).mean(),
            t,
        ),
    )


def quantiles(values: list[float]) -> dict:
    return {str(q): float(np.quantile(values, q)) if values else None for q in (0.5, 0.9, 0.95)}


def metrics(pairs: list[tuple[str, str]], states: list[str]) -> dict:
    matrix = {
        actual: {pred: sum(a == actual and p == pred for a, p in pairs) for pred in states}
        for actual in states
    }
    per_class = {}
    for state in states:
        tp = matrix[state][state]
        support = sum(matrix[state].values())
        predicted = sum(matrix[s][state] for s in states)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        per_class[state] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        }
    return {
        "confusion_matrix": matrix,
        "per_class": per_class,
        "macro_f1": sum(v["f1"] for v in per_class.values()) / len(states),
        "balanced_accuracy": sum(v["recall"] for v in per_class.values()) / len(states),
        "accuracy": sum(a == p for a, p in pairs) / len(pairs) if pairs else None,
    }


def evaluate(rows: list[dict], protocol: dict) -> tuple[dict, list[dict]]:
    policy = protocol["label_policy"]
    states = protocol["states"]
    ledgers = {group: [] for group in protocol["groups"]}
    folds = []
    for index, (train, test, definition) in enumerate(v2.folds(rows, protocol)):
        floor = label_scale(train, policy)
        actual = [state_label(r, floor, policy) for r in test]
        fold = {
            **definition,
            "fold": index,
            "label_floor": floor,
            "distribution": dict(Counter(actual)),
            "groups": {},
        }
        for group, names in protocol["groups"].items():
            temperature = calibration_temperature(train, policy, names, protocol)
            model = Logit(names, states, protocol["model_parameters"]).fit(
                train, [state_label(r, floor, policy) for r in train]
            )
            probabilities = model.probabilities(test, temperature)
            predicted = [states[int(np.argmax(p))] for p in probabilities]
            fold["groups"][group] = {
                "temperature": temperature,
                "fit_means": model.mean.tolist(),
                "fit_scales": model.scale.tolist(),
                "coefficients": model.weights.tolist(),
                "metrics": metrics(list(zip(actual, predicted, strict=True)), states),
            }
            for r, a, p, probs in zip(test, actual, predicted, probabilities, strict=True):
                ledgers[group].append((r, a, p, float(max(probs)), index, probs.tolist(), floor))
        folds.append(fold)
    summary = {}
    for group, entries in ledgers.items():
        pairs = [(a, p) for _, a, p, *_ in entries]
        summary[group] = metrics(pairs, states)
    entries = ledgers["D"]
    distribution = {s: sum(a == s for _, a, *_ in entries) for s in states}
    by_symbol = {
        sym: dict(Counter(a for r, a, *_ in entries if r["symbol"] == sym))
        for sym in sorted({r["symbol"] for r, *_ in entries})
    }
    behavior = {}
    for state in states:
        subset = [r for r, a, *_ in entries if a == state]
        errors = [
            10000 * (reality_return(r) - (r["outcome"] / r["previous_native_close"] - 1))
            for r in subset
        ]
        ratios = [
            (r["outcome"] / r["previous_native_close"] - 1) / reality_return(r)
            for r in subset
            if abs(reality_return(r)) > 1e-12
        ]
        behavior[state] = {
            "count": len(subset),
            "mark_absolute_error_bps": float(np.mean(np.abs(errors))) if errors else None,
            "mark_signed_error_bps": float(np.mean(errors)) if errors else None,
            "mark_error_quantiles_bps": quantiles([abs(e) for e in errors]),
            "reopen_direction_agreement": sum(
                reality_return(r) * (r["outcome"] / r["previous_native_close"] - 1) > 0
                for r in subset
            )
            / len(subset)
            if subset
            else None,
            "transfer_ratio_median": float(np.median(ratios)) if ratios else None,
        }
    buckets = {}
    for name, (low, high) in protocol["confidence_buckets"].items():
        subset = [
            (r, a, p, c) for r, a, p, c, *_ in entries if low <= c < high or (high == 1 and c == 1)
        ]
        buckets[name] = {
            "count": len(subset),
            "mean_confidence": float(np.mean([c for _, _, _, c in subset])) if subset else None,
            "classification_reliability": sum(a == p for _, a, p, _ in subset) / len(subset)
            if subset
            else None,
            "mark_absolute_error_bps": float(
                np.mean(
                    [
                        abs(
                            10000
                            * (reality_return(r) - (r["outcome"] / r["previous_native_close"] - 1))
                        )
                        for r, *_ in subset
                    ]
                )
            )
            if subset
            else None,
            "direction_agreement": sum(
                reality_return(r) * (r["outcome"] / r["previous_native_close"] - 1) > 0
                for r, *_ in subset
            )
            / len(subset)
            if subset
            else None,
        }
    ledger = [
        {
            "symbol": r["symbol"],
            "decision_timestamp": r["decision_timestamp"],
            "fair_value_reference_version": protocol["fair_value_reference_version"],
            "discovery_state": p,
            "state_model_version": protocol["state_model_version"],
            "discovery_confidence": c,
            "confidence_version": protocol["confidence_version"],
            "feature_set_version": protocol["feature_set_version"],
            "fold": index,
            "input_provenance": r["input_refs"],
            "class_probabilities": dict(zip(states, probs, strict=True)),
        }
        for r, _, p, c, index, probs, _ in entries
    ]
    return {
        "folds": folds,
        "distribution": distribution,
        "distribution_percent": {s: 100 * n / len(entries) for s, n in distribution.items()},
        "distribution_by_symbol": by_symbol,
        "distribution_by_symbol_percent": {
            sym: {s: 100 * counts.get(s, 0) / sum(counts.values()) for s in states}
            for sym, counts in by_symbol.items()
        },
        "state_behavior": behavior,
        "ablations": summary,
        "confidence_buckets": buckets,
        "scored_rows": len(entries),
        "label_floor_by_fold": [f["label_floor"] for f in folds],
        "acceptance_decision": "DISCOVERY_STATE_V1_NOT_JUSTIFIED",
        "acceptance_reason": (
            "Four outcome-defined states separate descriptively but the full classifier "
            "has zero OVERSHOOT recall; confidence does not monotonically reduce mark error."
        ),
        "confidence_reliability_monotone": all(
            buckets[a]["classification_reliability"] is not None
            and buckets[c]["classification_reliability"] is not None
            and buckets[a]["classification_reliability"] <= buckets[c]["classification_reliability"]
            for a, c in (("LOW", "MEDIUM"), ("MEDIUM", "HIGH"))
        ),
        "confidence_mark_error_monotone": all(
            buckets[a]["mark_absolute_error_bps"] is not None
            and buckets[c]["mark_absolute_error_bps"] is not None
            and buckets[a]["mark_absolute_error_bps"] >= buckets[c]["mark_absolute_error_bps"]
            for a, c in (("LOW", "MEDIUM"), ("MEDIUM", "HIGH"))
        ),
        "source_leadership": (
            "NOT_ESTIMATED: one Reality path and one native context; "
            "no independent source leadership inference"
        ),
    }, ledger


def run() -> dict:
    protocol, manifest, calendar = load_protocol()
    parent, _, _ = v2.load_protocol()
    bounds = v2.research_bounds(parent)
    rows = fv.rows_for_bounds(manifest, calendar, bounds)
    if not rows or any(
        not bounds[0] <= b.timestamp(r["decision_timestamp"]) < bounds[1] for r in rows
    ):
        raise ValueError("FINAL_OOS_LOCKED")
    add_path_features(rows, manifest, calendar)
    analysis, ledger = evaluate(rows, protocol)
    hashes = {
        str(p.relative_to(b.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            Path(__file__),
            CONTRACT,
            b.ROOT / "research/fair_value.py",
            b.ROOT / "research/fair_value_v2.py",
            b.ROOT / "research/baselines.py",
        )
    }
    hashes.update(
        {
            p: hashlib.sha256((b.ROOT / p).read_bytes()).hexdigest()
            for p in manifest["identity"]["source_file_hashes"]
        }
    )
    identity = {
        "dataset_version": protocol["dataset_version"],
        "protocol_version": protocol["protocol_version"],
        "state_label_version": protocol["state_label_version"],
        "feature_set_version": protocol["feature_set_version"],
        "state_model_version": protocol["state_model_version"],
        "confidence_version": protocol["confidence_version"],
        "fair_value_reference_version": protocol["fair_value_reference_version"],
        "fair_value_reference_definition": protocol["fair_value_reference_definition"],
        "fold_policy": protocol["folds"],
        "parameters": {
            "labels": protocol["label_policy"],
            "model": protocol["model_parameters"],
            "confidence_buckets": protocol["confidence_buckets"],
        },
        "source_hashes": hashes,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=b.ROOT, text=True
        ).strip(),
    }
    experiment_id = digest(identity)
    ledger = [{**r, "experiment_id": experiment_id} for r in ledger]
    report = {
        **identity,
        **analysis,
        "experiment_id": experiment_id,
        "claim_label": CLAIM,
        "mode": "RETROSPECTIVE_EVENT_TIME_DIAGNOSTIC",
        "model_eligible_observations": 0,
        "final_oos_evaluated": False,
        "pre_oos_rows": len(rows),
        "state_records_sha256": digest(ledger),
    }
    directory = b.ROOT / ".local-data/research/experiments" / experiment_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, data in (
        ("discovery-state-v1-records.json", ledger),
        ("discovery-state-v1-result.json", report),
    ):
        path = directory / name
        if path.exists():
            if json.loads(path.read_text()) != data:
                raise ValueError("Existing experiment differs; preserved")
        else:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
    return report


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "decision_metrics": result["ablations"]["D"],
                "distribution": result["distribution"],
                "confidence_buckets": result["confidence_buckets"],
            },
            indent=2,
        )
    )
