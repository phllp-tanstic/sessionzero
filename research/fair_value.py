"""Private, retrospective-estimated Fair Value research; final OOS is unsupported."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sessionzero_database.dataset_artifacts import digest
from sessionzero_market_data.source_sessions import CuratedBitgetSourceSessionProvider

from research import baselines as b

VERSION = "fair_value_model.v1"
FEATURE_VERSION = "fair_value_event_time.v1"
CLAIM = "RETROSPECTIVE ESTIMATED"
GROUPS = {
    "DISPLACEMENT": ("displacement",),
    "PATH": ("displacement", "momentum_3h", "range", "reversal"),
    "NATIVE": ("displacement", "momentum_3h", "range", "reversal", "native_day", "prior_gap"),
    "FULL": (
        "displacement",
        "momentum_3h",
        "range",
        "reversal",
        "native_day",
        "prior_gap",
        "mark_age_hours",
        "missing_fraction",
        "prior_gap_missing",
    ),
}
PARAMETERS = {
    "ridge_alpha": 1.0,
    "huber_delta": 1.5,
    "huber_iterations": 12,
    "internal_train_fraction": 0.6,
    "selection_metric": "bps_mae",
    "missing_policy": "development-mean-imputation; optional missing indicator",
}
FEATURE_SPEC = {
    "displacement": ("M/A - 1", "Reality close at exact prior cash close A and latest M"),
    "momentum_3h": ("M / first recent bar open - 1", "Reality OHLC last <=3 hours"),
    "range": ("(off-session max high - min low)/A", "Reality off-session OHLC"),
    "reversal": ("M / off-session max high - 1", "Reality off-session OHLC"),
    "native_day": ("previous native close / same-session open - 1", "native prior session"),
    "prior_gap": ("previous native open / earlier native close - 1", "native trailing sessions"),
    "mark_age_hours": ("(decision - latest bar completion) / hour", "Reality completion"),
    "missing_fraction": ("(hourly grid - observed) / hourly grid", "Reality completion grid"),
    "prior_gap_missing": ("1 if prior native open or earlier close absent else 0", "native status"),
}


def eligible_candles(observations: list[dict], close_time: datetime, decision: datetime) -> dict:
    """Return only complete off-session bars; reject duplicate completion instants."""
    result = {}
    for observation in observations:
        candle = observation["candle"]
        completion = b.timestamp(candle["event_time"]) + timedelta(hours=1)
        if close_time <= completion < decision:
            if completion in result:
                raise ValueError("Duplicate Reality completion")
            result[completion] = candle
    return result


def feature_vector(
    candles: dict,
    close_time: datetime,
    decision: datetime,
    previous_close: float,
    previous_open: float | None,
    prior_close: float | None,
) -> tuple[dict, dict] | None:
    """Only event-time inputs. Historical revision availability is NOT certified."""
    if previous_close <= 0 or any(t < close_time or t >= decision for t in candles):
        raise ValueError("Future or invalid feature input")
    if close_time not in candles:
        return None  # exact anchor, never substituted
    times = sorted(candles)
    anchor = float(candles[close_time]["close"])
    mark_time = times[-1]
    mark = float(candles[mark_time]["close"])
    if anchor <= 0 or mark <= 0:
        raise ValueError("Invalid Reality price")
    recent = [t for t in times if mark_time - timedelta(hours=3) <= t <= mark_time]
    highs = [float(candles[t]["high"]) for t in times]
    lows = [float(candles[t]["low"]) for t in times]
    start = float(candles[recent[0]]["open"])
    expected = int((decision - close_time).total_seconds() // 3600)
    features = {
        "displacement": mark / anchor - 1,
        "momentum_3h": mark / start - 1,
        "range": (max(highs) - min(lows)) / anchor,
        "reversal": mark / max(highs) - 1,
        "native_day": previous_close / previous_open - 1 if previous_open else None,
        "prior_gap": previous_open / prior_close - 1 if previous_open and prior_close else None,
        "mark_age_hours": (decision - mark_time).total_seconds() / 3600,
        "missing_fraction": (expected - len(times)) / expected if expected else 0,
        "prior_gap_missing": float(previous_open is None or prior_close is None),
    }
    refs = {
        "reality_anchor_completion": close_time.isoformat(),
        "reality_latest_completion": mark_time.isoformat(),
        "reality_candle_count": len(times),
        "previous_close_time": close_time.isoformat(),
        "historical_availability": "UNKNOWN_AVAILABILITY",
        "reality_input_hash": digest([candles[t] for t in times]),
    }
    return features, refs


def rows_for_partition(
    protocol: dict, manifest: dict, calendar: dict, partition: str
) -> list[dict]:
    bounds = b.partition_bounds(protocol, partition)  # fail before any archive access
    provider = CuratedBitgetSourceSessionProvider()
    sessions = calendar["sessions"]
    selected = [
        (i, sessions[i - 1], session)
        for i, session in enumerate(sessions)
        if i and session["role"] == "EVALUATION" and b.in_partition(session, bounds)
    ]
    rows = []
    for member in manifest["identity"]["members"]:
        symbol = member["symbol"]
        native = {
            r["session"]["session_date"]: r
            for r in b.read_archive(manifest, f"native-{symbol}.json")["rows"]
            if b.timestamp(r["session"]["regular_open"]) < bounds[1]
        }
        observations = b.read_archive(manifest, f"reality-{symbol}.json")["observations"]
        for i, previous, session in selected:
            decision = b.decision_time(session)
            close_time = b.timestamp(previous["regular_close"])
            close = b.native_price(
                native.get(previous["session_date"]), "close", close_time - timedelta(minutes=1)
            )
            if close is None:
                continue
            if not b.source_path_known(provider, symbol, close_time, decision):
                continue
            candles = eligible_candles(observations, close_time, decision)
            prior = sessions[i - 2] if i >= 2 else None
            prior_close = (
                b.native_price(
                    native.get(prior["session_date"]),
                    "close",
                    b.timestamp(prior["regular_close"]) - timedelta(minutes=1),
                )
                if prior
                else None
            )
            previous_open = b.native_price(
                native.get(previous["session_date"]), "open", b.timestamp(previous["regular_open"])
            )
            extracted = feature_vector(
                candles, close_time, decision, close, previous_open, prior_close
            )
            if extracted is None:
                continue
            features, refs = extracted
            refs["native_previous_session_hash"] = digest(native[previous["session_date"]])
            if prior and prior["session_date"] in native:
                refs["native_earlier_session_hash"] = digest(native[prior["session_date"]])
            anchor = float(candles[close_time]["close"])
            mark = float(candles[max(candles)]["close"])
            # The target is read only after the prediction-input structure is complete.
            outcome = b.native_price(
                native.get(session["session_date"]), "open", b.timestamp(session["regular_open"])
            )
            if outcome is None:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "decision_timestamp": decision.isoformat(),
                    "previous_native_close": close,
                    "features": features,
                    "input_refs": refs,
                    "baselines": b.predict(close, mark, anchor),
                    "outcome": outcome,
                }
            )
    return sorted(rows, key=lambda r: (r["decision_timestamp"], r["symbol"]))


class LinearModel:
    def __init__(self, names: tuple[str, ...], robust: bool):
        self.names, self.robust = names, robust

    def matrix(self, rows: list[dict]) -> np.ndarray:
        return np.array(
            [
                [float("nan") if r["features"][n] is None else r["features"][n] for n in self.names]
                for r in rows
            ],
            dtype=float,
        ).reshape(-1, len(self.names))

    def fit(self, rows: list[dict]) -> LinearModel:
        if not rows:
            raise ValueError("Empty development fit")
        x = self.matrix(rows)
        self.mean = np.nanmean(x, axis=0)
        self.mean = np.where(np.isfinite(self.mean), self.mean, 0)
        x = np.where(np.isnan(x), self.mean, x)
        self.scale = np.std(x, axis=0)
        self.scale = np.where(self.scale > 1e-12, self.scale, 1)
        design = np.column_stack([np.ones(len(x)), (x - self.mean) / self.scale])
        y = np.array([r["outcome"] / r["previous_native_close"] - 1 for r in rows])
        penalty = np.diag([0, *([PARAMETERS["ridge_alpha"]] * len(self.names))])
        weights = np.ones(len(x))
        for _ in range(PARAMETERS["huber_iterations"] if self.robust else 1):
            self.coef = np.linalg.solve(
                design.T @ (weights[:, None] * design) + penalty, design.T @ (weights * y)
            )
            residual = y - design @ self.coef
            mad = statistics.median(abs(residual - statistics.median(residual)))
            cutoff = PARAMETERS["huber_delta"] * max(1.4826 * mad, 1e-6)
            weights = np.minimum(1, cutoff / np.maximum(abs(residual), 1e-12))
        return self

    def predict(self, rows: list[dict]) -> np.ndarray:
        x = self.matrix(rows)
        x = np.where(np.isnan(x), self.mean, x)
        return self.coef[0] + ((x - self.mean) / self.scale) @ self.coef[1:]


def internal_split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    dates = sorted({r["decision_timestamp"] for r in rows})
    boundary = dates[int(len(dates) * PARAMETERS["internal_train_fraction"])]
    train = [r for r in rows if r["decision_timestamp"] < boundary]
    holdout = [r for r in rows if r["decision_timestamp"] >= boundary]
    if not train or not holdout:
        raise ValueError("Insufficient chronological development dates")
    return train, holdout


def score(rows: list[dict], predictions: list[float]) -> dict:
    return b.metrics(
        [
            (p, r["outcome"], r["previous_native_close"])
            for r, p in zip(rows, predictions, strict=True)
        ]
    )


def evaluate_models(development: list[dict], validation: list[dict]) -> tuple[dict, dict, list]:
    train, internal = internal_split(development)
    candidates = {}
    for group, names in GROUPS.items():
        for kind in ("RIDGE", "HUBER"):
            key = f"{kind}_{group}"
            model = LinearModel(names, robust=kind == "HUBER").fit(train)
            pred = [
                float(r["previous_native_close"] * (1 + value))
                for r, value in zip(internal, model.predict(internal), strict=True)
            ]
            candidates[key] = {
                "internal": score(internal, pred),
                "features": list(names),
                "parameters": len(names) + 1,
                "fit_samples": len(train),
            }
    # Declared selection uses development only; prefer simpler candidate on exact ties.
    selected = min(
        candidates,
        key=lambda key: (
            candidates[key]["internal"]["bps"]["mae"],
            candidates[key]["parameters"],
            key,
        ),
    )
    results = {}
    predictions = []
    for group, names in GROUPS.items():
        for kind in ("RIDGE", "HUBER"):
            key = f"{kind}_{group}"
            model = LinearModel(names, robust=kind == "HUBER").fit(development)
            dev_prices = [
                float(r["previous_native_close"] * (1 + v))
                for r, v in zip(development, model.predict(development), strict=True)
            ]
            val_prices = [
                float(r["previous_native_close"] * (1 + v))
                for r, v in zip(validation, model.predict(validation), strict=True)
            ]
            results[key] = {
                **candidates[key],
                "development": score(development, dev_prices),
                "validation": score(validation, val_prices),
                "fitted_intercept_and_coefficients": model.coef.tolist(),
                "development_feature_means": model.mean.tolist(),
                "development_feature_scales": model.scale.tolist(),
                "full_development_fit_samples": len(development),
                "validation_used_for_selection": False,
            }
            if key == selected:
                for partition, rows, prices in (
                    ("DEVELOPMENT", development, dev_prices),
                    ("VALIDATION", validation, val_prices),
                ):
                    for row, price in zip(rows, prices, strict=True):
                        predictions.append(prediction_record(row, price, key, partition))
    return (
        results,
        {
            "selected": selected,
            "train_dates": [train[0]["decision_timestamp"], train[-1]["decision_timestamp"]],
            "internal_dates": [
                internal[0]["decision_timestamp"],
                internal[-1]["decision_timestamp"],
            ],
            "train_count": len(train),
            "internal_count": len(internal),
        },
        predictions,
    )


def prediction_record(row: dict, price: float, key: str, partition: str) -> dict:
    predicted_return = price / row["previous_native_close"] - 1
    return {
        "symbol": row["symbol"],
        "decision_timestamp": row["decision_timestamp"],
        "partition": partition,
        "previous_native_close": row["previous_native_close"],
        "predicted_reopen_return": predicted_return,
        "predicted_fair_value_price": price,
        "fair_value_return": predicted_return,
        "fair_value_price": price,
        "model_version": VERSION + "." + key,
        "feature_set_version": FEATURE_VERSION,
        "input_provenance": row["input_refs"],
    }


def comparisons(rows: list[dict], prediction_records: list[dict]) -> dict:
    keys = {(p["symbol"], p["decision_timestamp"]): p for p in prediction_records}
    aligned = [r for r in rows if (r["symbol"], r["decision_timestamp"]) in keys]
    common = [r for r in aligned if all(v is not None for v in r["baselines"].values())]
    output = {}

    def price(r, name):
        if name == "FAIR_VALUE":
            return keys[r["symbol"], r["decision_timestamp"]]["fair_value_price"]
        return r["baselines"][name]

    for name in (*b.NAMES, "FAIR_VALUE"):
        specific = [r for r in aligned if price(r, name) is not None]
        output[name] = {
            "candidate": score(specific, [price(r, name) for r in specific]),
            "common": score(common, [price(r, name) for r in common]),
        }
    errors = sorted(
        (
            {
                "symbol": r["symbol"],
                "decision_timestamp": r["decision_timestamp"],
                "absolute_bps": abs(
                    10000 * (price(r, "FAIR_VALUE") - r["outcome"]) / r["previous_native_close"]
                ),
            }
            for r in aligned
        ),
        key=lambda x: -x["absolute_bps"],
    )
    ae = sorted(e["absolute_bps"] for e in errors)
    per_symbol = {
        symbol: {
            name: score(group, [price(r, name) for r in group]) for name in (*b.NAMES, "FAIR_VALUE")
        }
        for symbol in sorted({r["symbol"] for r in common})
        for group in [[r for r in common if r["symbol"] == symbol]]
    }
    return {
        "metrics": output,
        "per_symbol": per_symbol,
        "symbols_beating_reality_mark_bps_mae": sum(
            values["FAIR_VALUE"]["bps"]["mae"] < values["REALITY_MARK"]["bps"]["mae"]
            for values in per_symbol.values()
        ),
        "absolute_bps_quantiles": {
            str(q): ae[math.ceil(q * len(ae)) - 1] for q in (0.5, 0.9, 0.95, 0.99)
        }
        if ae
        else {},
        "worst_errors": errors[:10],
        "common_count": len(common),
    }


def run() -> dict:
    protocol, manifest, calendar = b.load_contract()
    if any(
        protocol["eligibility"][field]["role"] != "UNKNOWN_AVAILABILITY"
        or protocol["eligibility"][field]["model_eligible"]
        for field in ("previous_native_close", "reality_ohlcv")
    ):
        raise ValueError("Retrospective eligibility boundary changed")
    # Explicitly exercise both guards before touching any private archive.
    b.partition_bounds(protocol, "DEVELOPMENT")
    b.partition_bounds(protocol, "VALIDATION")
    development = rows_for_partition(protocol, manifest, calendar, "DEVELOPMENT")
    validation = rows_for_partition(protocol, manifest, calendar, "VALIDATION")
    results, selection, predictions = evaluate_models(development, validation)
    hashes = {
        str(p.relative_to(b.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__), b.ROOT / "research/baselines.py"]
    }
    hashes.update(
        {
            path: hashlib.sha256((b.ROOT / path).read_bytes()).hexdigest()
            for path in manifest["identity"]["source_file_hashes"]
        }
    )
    git_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=b.ROOT, text=True
    ).strip()
    identity = {
        "dataset_version": protocol["dataset_version"],
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": b.PROTOCOL_SHA256,
        "split_version": protocol["split_version"],
        "target_version": protocol["target_version"],
        "feature_set_version": FEATURE_VERSION,
        "model_version": VERSION,
        "parameters": PARAMETERS,
        "source_hashes": hashes,
        "random_seed": None,
        "git_commit": git_commit,
    }
    experiment_id = digest(identity)
    predictions = [
        {
            **p,
            "experiment_id": experiment_id,
            "dataset_version": protocol["dataset_version"],
            "split_version": protocol["split_version"],
        }
        for p in predictions
    ]
    report = {
        **identity,
        "experiment_id": experiment_id,
        "claim_label": CLAIM,
        "mode": "RETROSPECTIVE_EVENT_TIME_DIAGNOSTIC",
        "model_eligible_observations": 0,
        "feature_spec": {
            name: {
                "formula": formula,
                "source_fields": sources,
                "event_time_inputs": "strictly before decision; exact anchor allowed",
                "eligibility_rule": "retrospective diagnostic only; original availability UNKNOWN",
                "missingness": "exact anchor absent excludes; optional native uses fit mean",
                "normalization": "development-fit mean/std; zero-variance scale=1",
                "version": FEATURE_VERSION,
            }
            for name, (formula, sources) in FEATURE_SPEC.items()
        },
        "final_oos_evaluated": False,
        "selection": selection,
        "candidate_results": results,
        "development_comparison": comparisons(
            development, [p for p in predictions if p["partition"] == "DEVELOPMENT"]
        ),
        "validation_comparison": comparisons(
            validation, [p for p in predictions if p["partition"] == "VALIDATION"]
        ),
        "development_count": len(development),
        "validation_count": len(validation),
        "predictions_sha256": digest(predictions),
        "git_commit_semantics": "BASE_COMMIT_PLUS_EXACT_SOURCE_HASHES",
    }
    directory = b.ROOT / ".local-data/research/experiments" / experiment_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, data in (
        ("fair-value-predictions.json", predictions),
        ("fair-value-result.json", report),
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # no partition or final-OOS override
    report = run()
    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "claim_label": CLAIM,
                "selection": report["selection"],
                "validation_comparison": report["validation_comparison"]["metrics"],
                "report": str(
                    b.ROOT
                    / ".local-data/research/experiments"
                    / report["experiment_id"]
                    / "fair-value-result.json"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
