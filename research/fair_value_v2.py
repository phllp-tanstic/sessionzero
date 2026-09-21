"""Private pre-OOS, expanding-window Fair Value V2 diagnostic. No OOS interface."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np
from sessionzero_database.dataset_artifacts import digest

from research import baselines as b
from research import fair_value as v1

CONTRACT = b.ROOT / "research/protocols/fair-value-v2.json"
CLAIM = "RETROSPECTIVE ESTIMATED"


def load_protocol() -> tuple[dict, dict, dict]:
    # Verify the frozen v1 baseline and accepted dataset before any private archive read.
    baseline, manifest, calendar = b.load_contract()
    protocol = json.loads(CONTRACT.read_text())
    if protocol["baseline_protocol_sha256"] != b.PROTOCOL_SHA256:
        raise ValueError("Baseline protocol identity changed")
    if protocol["dataset_version"] != baseline["dataset_version"]:
        raise ValueError("Dataset identity changed")
    if (
        protocol["historical_partitions"]
        != {key: baseline["splits"][key] for key in ("DEVELOPMENT", "VALIDATION")}
        or protocol["splits"]["FINAL_OOS"] != baseline["splits"]["FINAL_OOS"]
    ):
        raise ValueError("Historical partitions or final OOS changed")
    if protocol["splits"]["PRE_OOS_RESEARCH"] != [
        baseline["splits"]["DEVELOPMENT"][0],
        baseline["splits"]["VALIDATION"][1],
    ]:
        raise ValueError("Pre-OOS split differs from historical union")
    for field in ("previous_native_close", "reality_ohlcv"):
        if baseline["eligibility"][field] != {
            "model_eligible": False,
            "role": "UNKNOWN_AVAILABILITY",
        }:
            raise ValueError("Retrospective availability boundary changed")
    return protocol, manifest, calendar


def research_bounds(protocol: dict) -> tuple:
    start, end = map(b.timestamp, protocol["splits"]["PRE_OOS_RESEARCH"])
    oos_start, _ = map(b.timestamp, protocol["splits"]["FINAL_OOS"])
    if start >= end or end != oos_start or oos_start != b.timestamp("2026-08-14T20:00:00Z"):
        raise ValueError("FINAL_OOS_LOCKED")
    return start, end


def displacement(row: dict) -> float:
    return float(row["features"]["displacement"])


def design(row: dict, kind: str, knot: float) -> list[float]:
    x = displacement(row)
    if kind == "PIECEWISE_TRANSFER":
        # Fixed symmetric hinge; no validation-selected knot or additional data source.
        return [x, math.copysign(max(abs(x) - knot, 0), x)]
    return [x]


class TransferModel:
    def __init__(self, kind: str, parameters: dict):
        if kind not in ("SHRUNK_TRANSFER", "ROBUST_TRANSFER", "PIECEWISE_TRANSFER"):
            raise ValueError("Unknown candidate")
        self.kind, self.parameters = kind, parameters

    def fit(self, rows: list[dict]) -> TransferModel:
        if not rows:
            raise ValueError("Empty training set")
        knot = self.parameters["piecewise_knot_absolute_return"]
        x = np.asarray([design(r, self.kind, knot) for r in rows])
        self.mean = x.mean(axis=0)
        self.scale = np.where(x.std(axis=0) > 1e-12, x.std(axis=0), 1)
        matrix = np.column_stack([np.ones(len(rows)), (x - self.mean) / self.scale])
        y = np.asarray([r["outcome"] / r["previous_native_close"] - 1 for r in rows])
        penalty = np.diag([0, *([self.parameters["ridge_alpha"]] * x.shape[1])])
        weights = np.ones(len(rows))
        for _ in range(
            self.parameters["huber_iterations"] if self.kind == "ROBUST_TRANSFER" else 1
        ):
            self.coef = np.linalg.solve(
                matrix.T @ (weights[:, None] * matrix) + penalty, matrix.T @ (weights * y)
            )
            residual = y - matrix @ self.coef
            median = np.median(residual)
            mad = np.median(np.abs(residual - median))
            cutoff = self.parameters["huber_delta"] * max(1.4826 * mad, 1e-6)
            weights = np.minimum(1, cutoff / np.maximum(np.abs(residual), 1e-12))
        return self

    def predict_return(self, row: dict) -> float:
        x = np.asarray(design(row, self.kind, self.parameters["piecewise_knot_absolute_return"]))
        return float(self.coef[0] + ((x - self.mean) / self.scale) @ self.coef[1:])

    def parameters_record(self) -> dict:
        return {
            "coefficients": self.coef.tolist(),
            "means": self.mean.tolist(),
            "scales": self.scale.tolist(),
            "ridge_alpha": self.parameters["ridge_alpha"],
            "knot": self.parameters["piecewise_knot_absolute_return"]
            if self.kind == "PIECEWISE_TRANSFER"
            else None,
        }


def folds(rows: list[dict], protocol: dict) -> list[tuple[list[dict], list[dict], dict]]:
    dates = sorted({r["decision_timestamp"] for r in rows})
    config = protocol["folds"]
    result = []
    for start in range(config["initial_train_dates"], len(dates), config["test_dates_per_fold"]):
        train = [r for r in rows if r["decision_timestamp"] < dates[start]]
        test = [
            r
            for r in rows
            if dates[start]
            <= r["decision_timestamp"]
            < (
                dates[min(start + config["test_dates_per_fold"], len(dates))]
                if start + config["test_dates_per_fold"] < len(dates)
                else "9999"
            )
        ]
        if not test or len(train) < config["minimum_train_rows"]:
            raise ValueError("Insufficient chronological fit")
        # First-minute label completes one hour and one minute after decision.
        latest_train_label = max(
            b.timestamp(r["decision_timestamp"]) + timedelta(hours=1, minutes=1) for r in train
        )
        first_test = b.timestamp(test[0]["decision_timestamp"])
        if latest_train_label >= first_test:
            raise ValueError("Training outcome not available before test decision")
        definition = {
            "fit_start": train[0]["decision_timestamp"],
            "fit_end_exclusive": dates[start],
            "test_start": test[0]["decision_timestamp"],
            "test_end_inclusive": test[-1]["decision_timestamp"],
            "latest_fit_outcome_completion": latest_train_label.isoformat(),
            "fit_count": len(train),
            "prediction_count": len(test),
        }
        result.append((train, test, definition))
    return result


def metric(rows: list[dict], predictions: list[float]) -> dict:
    values = [
        (p, r["outcome"], r["previous_native_close"])
        for r, p in zip(rows, predictions, strict=True)
    ]
    result = b.metrics(values)
    errors = sorted(abs(10000 * (p - y) / c) for p, y, c in values)
    result["bps_error_p90"] = errors[math.ceil(0.9 * len(errors)) - 1] if errors else None
    result["bps_error_p95"] = errors[math.ceil(0.95 * len(errors)) - 1] if errors else None
    return result


def diagnostics(rows: list[dict]) -> dict:
    """Predeclared descriptive bins, never fed into candidate selection."""

    def grouped(key):
        groups = defaultdict(list)
        for r in rows:
            groups[key(r)].append(r)
        return {
            str(k): {
                "count": len(v),
                "mark": metric(v, [r["baselines"]["REALITY_MARK"] for r in v]),
                "transfer": metric(v, [r["baselines"]["REALITY_RETURN_TRANSFER"] for r in v]),
            }
            for k, v in sorted(groups.items())
        }

    x = np.array([displacement(r) for r in rows])
    y = np.array([r["outcome"] / r["previous_native_close"] - 1 for r in rows])
    slope, intercept = np.polyfit(x, y, 1)
    tails = sorted(
        abs(10000 * (r["baselines"]["REALITY_MARK"] - r["outcome"]) / r["previous_native_close"])
        for r in rows
    )
    return {
        "calibration": {"intercept": float(intercept), "slope": float(slope), "count": len(rows)},
        "conditional": {
            "displacement_bps": grouped(
                lambda r: (
                    "<50"
                    if abs(displacement(r)) < 0.005
                    else "50-200"
                    if abs(displacement(r)) < 0.02
                    else ">=200"
                )
            ),
            "symbol": grouped(lambda r: r["symbol"]),
            "volatility_range": grouped(
                lambda r: (
                    "<100"
                    if r["features"]["range"] < 0.01
                    else "100-300"
                    if r["features"]["range"] < 0.03
                    else ">=300"
                )
            ),
            "prior_session_move": grouped(
                lambda r: (
                    "MISSING"
                    if r["features"]["native_day"] is None
                    else "<-100"
                    if r["features"]["native_day"] < -0.01
                    else ">100"
                    if r["features"]["native_day"] > 0.01
                    else "[-100,100]"
                )
            ),
        },
        "mark_absolute_bps_tails": {
            str(q): tails[math.ceil(q * len(tails)) - 1] for q in (0.5, 0.9, 0.95, 0.99)
        },
        "large_move_transfer": grouped(
            lambda r: (
                "positive"
                if displacement(r) >= 0.02
                else "negative"
                if displacement(r) <= -0.02
                else "interior"
            )
        ),
    }


def evaluate(rows: list[dict], protocol: dict) -> tuple[dict, list[dict]]:
    # Outcome-bearing rows are confined to fitting/scoring. Prediction records omit outcomes.
    results = {name: [] for name in protocol["candidates"]}
    ledger, definitions = [], []
    for index, (train, test, definition) in enumerate(folds(rows, protocol)):
        fit = {}
        for name in protocol["candidates"]:
            model = (
                TransferModel(name, protocol["parameters"]).fit(train)
                if name != "REALITY_MARK"
                else None
            )
            prices = (
                [r["baselines"]["REALITY_MARK"] for r in test]
                if model is None
                else [r["previous_native_close"] * (1 + model.predict_return(r)) for r in test]
            )
            fit[name] = {
                "fit_count": len(train) if model else 0,
                "prediction_count": len(test),
                "parameters": model.parameters_record() if model else {},
                "metrics": metric(test, prices),
            }
            for r, price in zip(test, prices, strict=True):
                record = {
                    "symbol": r["symbol"],
                    "decision_timestamp": r["decision_timestamp"],
                    "fold": index,
                    "model": name,
                    "prediction": price,
                    "predicted_return": price / r["previous_native_close"] - 1,
                    "input_refs": r["input_refs"],
                }
                ledger.append(record)
                results[name].append((r, price, index))
        definitions.append({**definition, "candidates": fit})
    summaries = {}
    for name, triples in results.items():
        subset = [r for r, _, _ in triples]
        prices = [p for _, p, _ in triples]
        per_symbol = {
            symbol: metric(
                [r for r in subset if r["symbol"] == symbol],
                [p for r, p in zip(subset, prices, strict=True) if r["symbol"] == symbol],
            )
            for symbol in sorted({r["symbol"] for r in subset})
        }
        summaries[name] = {"overall": metric(subset, prices), "per_symbol": per_symbol}
    mark = summaries["REALITY_MARK"]
    decisions = {}
    for name, summary in summaries.items():
        if name == "REALITY_MARK":
            continue
        symbol_delta = {
            s: summary["per_symbol"][s]["bps"]["mae"] - mark["per_symbol"][s]["bps"]["mae"]
            for s in mark["per_symbol"]
        }
        folds_better = sum(
            d["candidates"][name]["metrics"]["bps"]["mae"]
            < d["candidates"]["REALITY_MARK"]["metrics"]["bps"]["mae"]
            for d in definitions
        )
        decisions[name] = {
            "mae_improves": summary["overall"]["bps"]["mae"] < mark["overall"]["bps"]["mae"],
            "rmse_improves": summary["overall"]["bps"]["rmse"] < mark["overall"]["bps"]["rmse"],
            "symbols_improved": sum(v < 0 for v in symbol_delta.values()),
            "symbols_improved_or_neutral_within_1bps": sum(v <= 1 for v in symbol_delta.values()),
            "symbol_mae_delta_bps": symbol_delta,
            "folds_better_mae": folds_better,
            "fold_count": len(definitions),
            "p95_delta_bps": summary["overall"]["bps_error_p95"] - mark["overall"]["bps_error_p95"],
        }
    # Predeclared conservative rule; marginal/mixed evidence is explicitly not promotion.
    promotable = [
        n
        for n, d in decisions.items()
        if d["mae_improves"]
        and d["rmse_improves"]
        and (mark["overall"]["bps"]["mae"] - summaries[n]["overall"]["bps"]["mae"])
        / mark["overall"]["bps"]["mae"]
        >= protocol["promotion"]["minimum_relative_bps_mae_gain"]
        and (mark["overall"]["bps"]["rmse"] - summaries[n]["overall"]["bps"]["rmse"])
        / mark["overall"]["bps"]["rmse"]
        >= protocol["promotion"]["minimum_relative_bps_rmse_gain"]
        and d["symbols_improved_or_neutral_within_1bps"] >= 11
        and d["folds_better_mae"] >= math.ceil(0.75 * d["fold_count"])
        and d["p95_delta_bps"] <= 0
    ]
    selection = (
        min(promotable, key=lambda n: (summaries[n]["overall"]["bps"]["mae"], n))
        if promotable
        else None
    )
    return {
        "folds": definitions,
        "summaries": summaries,
        "promotion_checks": decisions,
        "selected": selection,
        "decision": "FAIR_VALUE_V2_PROMOTABLE_RETROSPECTIVE_ONLY"
        if selection
        else "FAIR_VALUE_V2_NOT_JUSTIFIED",
        "scored_rows": len(results["REALITY_MARK"]),
    }, ledger


def run() -> dict:
    protocol, manifest, calendar = load_protocol()
    bounds = research_bounds(protocol)  # before archive access
    rows = v1.rows_for_bounds(manifest, calendar, bounds)
    if not rows or any(
        not bounds[0] <= b.timestamp(r["decision_timestamp"]) < bounds[1] for r in rows
    ):
        raise ValueError("Research rows outside protected pre-OOS interval")
    analysis, ledger = evaluate(rows, protocol)
    hashes = {
        str(p.relative_to(b.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            Path(__file__),
            b.ROOT / "research/fair_value.py",
            b.ROOT / "research/baselines.py",
            CONTRACT,
        )
    }
    hashes.update(
        {
            p: hashlib.sha256((b.ROOT / p).read_bytes()).hexdigest()
            for p in manifest["identity"]["source_file_hashes"]
        }
    )
    identity = {
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": hashes[str(CONTRACT.relative_to(b.ROOT))],
        "dataset_version": protocol["dataset_version"],
        "split_version": protocol["split_version"],
        "target_version": protocol["target_version"],
        "feature_set_version": protocol["feature_set_version"],
        "model_version": protocol["model_version"],
        "parameters": protocol["parameters"],
        "fold_policy": protocol["folds"],
        "promotion_policy": protocol["promotion"],
        "source_hashes": hashes,
        "random_seed": None,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=b.ROOT, text=True
        ).strip(),
    }
    experiment_id = digest(identity)
    ledger = [
        {
            **r,
            "experiment_id": experiment_id,
            "dataset_version": protocol["dataset_version"],
            "split_version": protocol["split_version"],
            "model_version": protocol["model_version"],
            "feature_set_version": protocol["feature_set_version"],
        }
        for r in ledger
    ]
    report = {
        **identity,
        **analysis,
        "experiment_id": experiment_id,
        "claim_label": CLAIM,
        "mode": "RETROSPECTIVE_EVENT_TIME_DIAGNOSTIC",
        "model_eligible_observations": 0,
        "historical_partitions": protocol["historical_partitions"],
        "splits": protocol["splits"],
        "diagnostics": diagnostics(rows),
        "candidate_count": len(protocol["candidates"]),
        "pre_oos_rows": len(rows),
        "final_oos_evaluated": False,
        "predictions_sha256": digest(ledger),
        "git_commit_semantics": "BASE_COMMIT_PLUS_EXACT_SOURCE_HASHES",
    }
    directory = b.ROOT / ".local-data/research/experiments" / experiment_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, data in (
        ("fair-value-v2-predictions.json", ledger),
        ("fair-value-v2-result.json", report),
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
                "report": str(
                    b.ROOT
                    / ".local-data/research/experiments"
                    / result["experiment_id"]
                    / "fair-value-v2-result.json"
                ),
                "decision": result["decision"],
                "scored_rows": result["scored_rows"],
                "metrics": {k: v["overall"] for k, v in result["summaries"].items()},
            },
            indent=2,
        )
    )
