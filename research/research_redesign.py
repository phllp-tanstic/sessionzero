"""Pre-OOS trajectory and formulation audit; no new fitted state or fair-value model."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from collections import Counter, defaultdict
from datetime import timedelta
from itertools import pairwise
from pathlib import Path

import numpy as np
from sessionzero_database.dataset_artifacts import digest
from sessionzero_market_data.source_sessions import CuratedBitgetSourceSessionProvider

from research import baselines as b
from research import discovery_state as ds
from research import fair_value as fv
from research import fair_value_v2 as v2

CONTRACT = b.ROOT / "research/protocols/research-redesign-v1.json"
CLAIM = "RETROSPECTIVE ESTIMATED"
STATES = ("DISCOVERY", "UNDERREACTION", "OVERSHOOT", "NOISE")


def protocol_and_inputs() -> tuple[dict, dict, dict]:
    parent, manifest, calendar = v2.load_protocol()
    bounds = v2.research_bounds(parent)
    protocol = json.loads(CONTRACT.read_text())
    if (
        protocol["parent_protocol_version"] != parent["protocol_version"]
        or protocol["dataset_version"] != parent["dataset_version"]
        or tuple(map(b.timestamp, protocol["split"])) != bounds
    ):
        raise ValueError("FINAL_OOS_LOCKED")
    return protocol, manifest, calendar


def grid(previous_close, next_open, slots: list[dict]) -> list[tuple[str, object]]:
    result = []
    for slot in slots:
        origin = previous_close if slot["reference"] == "PREVIOUS_CLOSE" else next_open
        timestamp = origin + timedelta(minutes=slot["minutes"])
        if not previous_close < timestamp < next_open:
            raise ValueError("Grid timestamp outside cash-closed interval")
        result.append((slot["name"], timestamp))
    if len({time for _, time in result}) != len(result):
        raise ValueError("Duplicate grid timestamps")
    return result


def path_features(candles: dict, close_time, evaluation, previous_close: float) -> dict:
    """Complete-hour event-time features only; no outcome parameter exists."""
    if previous_close <= 0 or close_time not in candles or not candles:
        raise ValueError("Missing exact anchor or previous close")
    if any(t < close_time or t >= evaluation for t in candles):
        raise ValueError("Future or pre-anchor bar in trajectory")
    times = sorted(candles)
    anchor = float(candles[close_time]["close"])
    marks = [float(candles[t]["close"]) for t in times]
    mark = marks[-1]
    returns = [math.log(right / left) for left, right in pairwise(marks)]
    travel = sum(abs(x) for x in returns)
    net = math.log(mark / anchor)
    highs = [float(candles[t]["high"]) for t in times]
    lows = [float(candles[t]["low"]) for t in times]
    expected = max(1, int((evaluation - close_time).total_seconds() // 3600))
    recent = [t for t in times if t >= times[-1] - timedelta(hours=3)]
    recent_start = float(candles[recent[0]]["open"])
    slope = float(np.polyfit(np.arange(len(marks)), np.log(marks), 1)[0]) if len(marks) > 1 else 0.0
    return {
        "mark": mark,
        "reality_displacement": mark / previous_close - 1,
        "cumulative_off_session_return": mark / anchor - 1,
        "path_efficiency": abs(net) / travel if travel else 0.0,
        "realized_volatility": math.sqrt(sum(x * x for x in returns)),
        "high_low_range": (max(highs) - min(lows)) / anchor,
        "distance_running_high": mark / max(highs) - 1,
        "distance_running_low": mark / min(lows) - 1,
        "momentum_3h": mark / recent_start - 1,
        "reversal_magnitude": max(highs) / mark - 1,
        "sign_changes": sum(a * c < 0 for a, c in pairwise(returns)),
        "trend_slope_log_per_bar": slope,
        "observation_count": len(times),
        "expected_hour_count": expected,
        "observation_density": len(times) / expected,
        "missing_fraction": max(0, expected - len(times)) / expected,
        "staleness_hours": (evaluation - times[-1]).total_seconds() / 3600,
    }


def extract(protocol: dict, manifest: dict, calendar: dict) -> tuple[list[dict], list[dict], dict]:
    start, end = map(b.timestamp, protocol["split"])
    if end > b.timestamp("2026-08-14T20:00:00Z") or start >= end:
        raise ValueError("FINAL_OOS_LOCKED")
    sessions = calendar["sessions"]
    selected = [
        (previous, current)
        for previous, current in pairwise(sessions)
        if b.in_partition(current, (start, end))
    ]
    provider = CuratedBitgetSourceSessionProvider()
    records, evaluations = [], []
    exclusions = Counter()
    for member in manifest["identity"]["members"]:
        symbol = member["symbol"]
        native = {
            row["session"]["session_date"]: row
            for row in b.read_archive(manifest, f"native-{symbol}.json")["rows"]
            if b.timestamp(row["session"]["regular_open"]) < end
        }
        observations = [
            row
            for row in b.read_archive(manifest, f"reality-{symbol}.json")["observations"]
            if b.timestamp(row["candle"]["event_time"]) + timedelta(hours=1) < end
        ]
        for previous, current in selected:
            close_time = b.timestamp(previous["regular_close"])
            open_time = b.timestamp(current["regular_open"])
            close = b.native_price(
                native.get(previous["session_date"]), "close", close_time - timedelta(minutes=1)
            )
            if close is None:
                exclusions["MISSING_PREVIOUS_NATIVE_CLOSE"] += len(protocol["slots"])
                continue
            # Outcome is read after constructing each outcome-free trajectory record.
            candidates = fv.eligible_candles(observations, close_time, open_time)
            for slot, evaluation in grid(close_time, open_time, protocol["slots"]):
                if not source_path_known(provider, symbol, close_time, evaluation):
                    exclusions[f"{slot}:SOURCE_PATH_UNKNOWN"] += 1
                    continue
                candles = {time: candle for time, candle in candidates.items() if time < evaluation}
                if close_time not in candles:
                    exclusions[f"{slot}:NO_EXACT_ANCHOR"] += 1
                    continue
                feature = path_features(candles, close_time, evaluation, close)
                record = {
                    "symbol": symbol,
                    "cash_session_date": current["session_date"],
                    "evaluation_timestamp": evaluation.isoformat(),
                    "slot": slot,
                    "previous_state": None,
                    "outcome_free_state_estimate": None,
                    "trajectory_features": feature,
                    "dataset_version": protocol["dataset_version"],
                    "protocol_version": protocol["protocol_version"],
                    "input_provenance": {
                        "previous_close_time": close_time.isoformat(),
                        "latest_reality_completion": max(candles).isoformat(),
                        "reality_path_hash": digest([candles[t] for t in sorted(candles)]),
                        "historical_availability": "UNKNOWN_AVAILABILITY",
                        "source_evidence_version": manifest["identity"][
                            "session_evidence_content_version"
                        ],
                    },
                }
                records.append(record)
                # Label/evaluation-only join, never serialized to trajectory records.
                outcome = b.native_price(native.get(current["session_date"]), "open", open_time)
                if outcome is None:
                    exclusions[f"{slot}:MISSING_FUTURE_OUTCOME"] += 1
                    continue
                evaluations.append(
                    {"record_index": len(records) - 1, "outcome": outcome, "previous_close": close}
                )
    return (
        records,
        evaluations,
        {
            "candidate_cash_sessions": len(selected),
            "candidate_symbols": len(manifest["identity"]["members"]),
            "exclusions": dict(sorted(exclusions.items())),
        },
    )


def source_path_known(provider, symbol, close_time, evaluation) -> bool:
    return b.source_path_known(provider, symbol, close_time, evaluation)


def label(r: float, o: float, floor: float, lower: float, upper: float) -> str:
    if floor <= 0 or not 0 < lower < 1 < upper:
        raise ValueError("Invalid label convention")
    if abs(r) <= floor or abs(o) <= floor or r * o <= 0:
        return "NOISE"
    ratio = o / r
    if ratio < lower:
        return "OVERSHOOT"
    if ratio > upper:
        return "UNDERREACTION"
    return "DISCOVERY"


def transition_matrix(sequences: list[list[str]]) -> dict:
    counts = {a: {c: 0 for c in STATES} for a in STATES}
    for sequence in sequences:
        for a, c in pairwise(sequence):
            counts[a][c] += 1
    probability = {
        a: {
            c: counts[a][c] / sum(counts[a].values()) if sum(counts[a].values()) else None
            for c in STATES
        }
        for a in STATES
    }
    return {
        "counts": counts,
        "conditional_probability": probability,
        "persistence": sum(counts[s][s] for s in STATES)
        / sum(sum(v.values()) for v in counts.values())
        if any(sum(v.values()) for v in counts.values())
        else None,
    }


def bin_name(value: float, boundaries: tuple[float, float]) -> str:
    return "LOW" if value < boundaries[0] else "MID" if value < boundaries[1] else "HIGH"


def grouped(rows: list[dict], key, metric) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[str(key(row))].append(row)
    return {k: {"count": len(v), **metric(v)} for k, v in sorted(groups.items())}


def summarize(rows: list[dict]) -> dict:
    errors = [abs(r["residual_bps"]) for r in rows]
    return {
        "mark_mae_bps": float(np.mean(errors)) if errors else None,
        "direction_agreement": sum(r["direction_agreement"] for r in rows) / len(rows)
        if rows
        else None,
        "overshoot_rate": sum(r["state"] == "OVERSHOOT" for r in rows) / len(rows)
        if rows
        else None,
    }


def analyze(protocol: dict, records: list[dict], evaluations: list[dict], extraction: dict) -> dict:
    policy = protocol["label_policy"]
    joined = []
    for item in evaluations:
        record = records[item["record_index"]]
        f = record["trajectory_features"]
        r = f["reality_displacement"]
        o = item["outcome"] / item["previous_close"] - 1
        joined.append(
            {
                "symbol": record["symbol"],
                "date": record["cash_session_date"],
                "slot": record["slot"],
                "timestamp": record["evaluation_timestamp"],
                "features": f,
                "r": r,
                "o": o,
                "residual_bps": 10000 * (o - r),
                "direction_agreement": r * o > 0,
            }
        )
    slots = [slot["name"] for slot in protocol["slots"]]
    dates = sorted({r["date"] for r in joined})
    fit_dates = set(dates[: policy["resolution_fit_sessions"]])
    scales = {}
    for slot in slots:
        fit = [r for r in joined if r["slot"] == slot and r["date"] in fit_dates]
        if not fit:
            raise ValueError(f"No development rows for {slot}")
        scales[slot] = {
            "floor": policy["noise_floor_fraction"] * float(np.median([abs(r["r"]) for r in fit])),
            "residual_band_bps": float(
                np.quantile(
                    [abs(r["residual_bps"]) for r in fit],
                    policy["residual_band_development_quantile"],
                )
            ),
        }
        if scales[slot]["floor"] <= 0:
            raise ValueError("Zero development label scale")
    for r in joined:
        scale = scales[r["slot"]]
        r["state"] = label(
            r["r"],
            r["o"],
            scale["floor"],
            policy["reference_ratio_lower"],
            policy["reference_ratio_upper"],
        )
        r["alternate_ratio_state"] = label(
            r["r"],
            r["o"],
            scale["floor"],
            policy["alternative_ratio_lower"],
            policy["alternative_ratio_upper"],
        )
        if abs(r["r"]) <= scale["floor"] or abs(r["o"]) <= scale["floor"] or r["r"] * r["o"] <= 0:
            r["residual_state"] = "NOISE"
        elif abs(r["residual_bps"]) <= scale["residual_band_bps"]:
            r["residual_state"] = "DISCOVERY"
        else:
            r["residual_state"] = "UNDERREACTION" if abs(r["o"]) > abs(r["r"]) else "OVERSHOOT"
    by_session = defaultdict(list)
    for row in joined:
        by_session[(row["symbol"], row["date"])].append(row)
    rank = {slot: i for i, slot in enumerate(slots)}
    sequences = [
        [
            r["state"]
            for r in sorted(items, key=lambda x: rank[x["slot"]])
            if r["slot"] != "OPEN_MINUS_30M"
        ]
        for items in by_session.values()
    ]
    complete = [items for items in by_session.values() if {r["slot"] for r in items} >= set(slots)]
    matched = [r for items in complete for r in items]
    levels = {
        name: tuple(
            float(x) for x in np.quantile([r["features"][name] for r in joined], [1 / 3, 2 / 3])
        )
        for name in ("path_efficiency", "realized_volatility")
    }
    overshoot = {
        "slot": grouped(joined, lambda r: r["slot"], summarize),
        "symbol": grouped(joined, lambda r: r["symbol"], summarize),
        "displacement": grouped(
            joined,
            lambda r: (
                "<50bps"
                if abs(r["r"]) < 0.005
                else "50-200bps"
                if abs(r["r"]) < 0.02
                else ">=200bps"
            ),
            summarize,
        ),
        "volatility": grouped(
            joined,
            lambda r: bin_name(r["features"]["realized_volatility"], levels["realized_volatility"]),
            summarize,
        ),
        "path_efficiency": grouped(
            joined,
            lambda r: bin_name(r["features"]["path_efficiency"], levels["path_efficiency"]),
            summarize,
        ),
    }
    slot_counts = {
        slot: dict(Counter(r["state"] for r in joined if r["slot"] == slot)) for slot in slots
    }
    sensitivity = {
        variant: {
            "changed": sum(r[variant] != r["state"] for r in joined),
            "total": len(joined),
            "by_slot": {
                slot: {
                    "changed": sum(r[variant] != r["state"] for r in joined if r["slot"] == slot),
                    "distribution": dict(Counter(r[variant] for r in joined if r["slot"] == slot)),
                }
                for slot in slots
            },
        }
        for variant in ("alternate_ratio_state", "residual_state")
    }
    continuous = {
        slot: {
            "count": len(v := [r for r in joined if r["slot"] == slot]),
            "median_absolute_displacement_bps": float(np.median([abs(r["r"]) * 10000 for r in v])),
            "median_absolute_residual_bps": float(np.median([abs(r["residual_bps"]) for r in v])),
            "median_realized_volatility_bps": float(
                np.median([r["features"]["realized_volatility"] * 10000 for r in v])
            ),
            "direction_agreement": sum(r["direction_agreement"] for r in v) / len(v),
            **summarize(v),
        }
        for slot in slots
    }
    return {
        "extraction": extraction,
        "trajectory_records": len(records),
        "outcome_joined_rows": len(joined),
        "distinct_symbol_cash_sessions": len(by_session),
        "distinct_cash_sessions": len({r["date"] for r in joined}),
        "complete_grid_symbol_sessions": len(complete),
        "fit_dates": sorted(fit_dates),
        "slot_scales": scales,
        "state_counts_by_slot": slot_counts,
        "continuous_by_slot": continuous,
        "matched_common_panel_by_slot": {
            slot: summarize([r for r in matched if r["slot"] == slot]) for slot in slots
        },
        "transition_matrix": transition_matrix(sequences),
        "transition_matrix_excludes_redundant_t_minus_30m": True,
        "label_sensitivity": sensitivity,
        "overshoot_audit": overshoot,
        "fair_value_conditioning": {
            "slot": grouped(joined, lambda r: r["slot"], summarize),
            "path_efficiency": overshoot["path_efficiency"],
            "volatility": overshoot["volatility"],
            "reversal": grouped(
                joined,
                lambda r: bin_name(
                    r["features"]["reversal_magnitude"],
                    tuple(
                        float(x)
                        for x in np.quantile(
                            [q["features"]["reversal_magnitude"] for q in joined], [1 / 3, 2 / 3]
                        )
                    ),
                ),
                summarize,
            ),
        },
        "label_role": "RETROSPECTIVE_EVALUATION_ONLY",
    }


def source_audit() -> dict:
    """Repository-evidence classification, not a live entitlement probe."""
    return {
        "BITGET_REALITY_1H": {
            "status": "AVAILABLE",
            "research_history": "accepted 21-symbol 1H archive",
            "independence": "primary continuous path",
            "pit": "historical as-known unknown",
            "rights": "public derived rights unverified",
        },
        "ALPACA_SIP_RAW_NATIVE": {
            "status": "AVAILABLE",
            "research_history": "exact cash boundary minutes, not continuous overnight path",
            "independence": "native cash trades, distinct venue and hours",
            "pit": "historical revisions possible",
            "rights": "private research provisional; public derived rights unverified",
        },
        "BITGET_STOCK_PERPETUAL": {
            "status": "DEGRADED",
            "research_history": (
                "public live endpoints verified; no accepted aligned cohort archive"
            ),
            "independence": "derivative, separate instrument but index may overlap other venues",
            "pit": "historical as-known unverified",
            "rights": "public derived rights unverified",
        },
        "BITGET_MCP_NATIVE": {
            "status": "DEGRADED",
            "research_history": (
                "user-reported adjusted daily bars only; no intraday overnight panel"
            ),
            "independence": "possible republished underlying; unverified",
            "pit": "unverified",
            "rights": "unverified",
        },
        "BITGET_STOCKPLUS": {
            "status": "GATED",
            "research_history": "no authenticated entitlement or accepted archive",
            "independence": "underlying cash feed; provenance unverified",
            "pit": "unverified",
            "rights": "gated",
        },
        "ALPACA_BOATS": {
            "status": "GATED",
            "research_history": "documented delayed historical feed; never requested or archived",
            "independence": "separate overnight venue, relationship to Reality untested",
            "pit": "unverified",
            "rights": "unverified",
        },
        "BITGET_INDEX_COMPONENTS": {
            "status": "DEGRADED",
            "research_history": "public AAPL components observed; no aligned archive",
            "independence": "composite may republish exchange/venue prices",
            "pit": "unverified",
            "rights": "unverified",
        },
    }


def capture_gaps(captured_fields: set[str]) -> list[str]:
    required = {
        "RAW_REALITY_PATH_OHLCV",
        "PER_BAR_COMPLETION_AND_INGESTION_TIMES",
        "MULTI_TIMESTAMP_SNAPSHOTS",
        "PER_TIMESTAMP_SOURCE_SESSION_EVIDENCE",
        "PREVIOUS_NATIVE_CLOSE",
        "LATER_OUTCOME_VERSION_LINK",
    }
    return sorted(required - captured_fields)


def v1_confidence_targets(protocol: dict, manifest: dict, calendar: dict) -> dict:
    """Re-evaluate the existing V1 model; no new model family or selection."""
    rows = fv.rows_for_bounds(manifest, calendar, tuple(map(b.timestamp, protocol["split"])))
    ds.add_path_features(rows, manifest, calendar)
    state_protocol = ds.load_protocol()[0]
    analysis, predictions = ds.evaluate(rows, state_protocol)
    by_key = {(row["symbol"], row["decision_timestamp"]): row for row in rows}
    scored = []
    for prediction in predictions:
        row = by_key[(prediction["symbol"], prediction["decision_timestamp"])]
        floor = analysis["folds"][prediction["fold"]]["label_floor"]
        actual = ds.state_label(row, floor, state_protocol["label_policy"])
        o = row["outcome"] / row["previous_native_close"] - 1
        r = ds.reality_return(row)
        scored.append(
            {
                "correct": actual == prediction["discovery_state"],
                "absolute_error_bps": abs(10000 * (o - r)),
                "direction_agreement": r * o > 0,
                "path_efficiency": row["features"]["path_efficiency"],
                "missing_fraction": row["features"]["missing_fraction"],
                "mark_age_hours": row["features"]["mark_age_hours"],
            }
        )
    bounds = tuple(
        float(x) for x in np.quantile([row["path_efficiency"] for row in scored], [1 / 3, 2 / 3])
    )

    def quality_summary(values: list[dict]) -> dict:
        return {
            "state_reliability": sum(v["correct"] for v in values) / len(values),
            "mark_mae_bps": float(np.mean([v["absolute_error_bps"] for v in values])),
            "direction_agreement": sum(v["direction_agreement"] for v in values) / len(values),
        }

    return {
        "confidence_buckets": analysis["confidence_buckets"],
        "path_efficiency": grouped(
            scored, lambda r: bin_name(r["path_efficiency"], bounds), quality_summary
        ),
        "path_missingness": grouped(
            scored,
            lambda r: "ANY_MISSING" if r["missing_fraction"] > 0 else "COMPLETE",
            quality_summary,
        ),
        "mark_age": grouped(
            scored,
            lambda r: "OLDER_THAN_1H" if r["mark_age_hours"] > 1 else "WITHIN_1H",
            quality_summary,
        ),
    }


def run() -> dict:
    protocol, manifest, calendar = protocol_and_inputs()  # guard before any archive access
    records, evaluations, extraction = extract(protocol, manifest, calendar)
    analysis = analyze(protocol, records, evaluations, extraction)
    analysis["source_diversity"] = source_audit()
    analysis["source_leadership_decision"] = "SOURCE_LEADERSHIP_NOT_INSTRUMENTED"
    analysis["prospective_capture_gaps"] = capture_gaps(
        {"PREVIOUS_NATIVE_CLOSE", "LATER_OUTCOME_VERSION_LINK", "REALITY_DECISION_MARK"}
    )
    analysis["v1_confidence_targets"] = v1_confidence_targets(protocol, manifest, calendar)
    hashes = {
        str(p.relative_to(b.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            Path(__file__),
            CONTRACT,
            b.ROOT / "research/baselines.py",
            b.ROOT / "research/fair_value.py",
            b.ROOT / "research/fair_value_v2.py",
            b.ROOT / "research/discovery_state.py",
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
        "dataset_version": protocol["dataset_version"],
        "parameters": protocol,
        "source_hashes": hashes,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=b.ROOT, text=True
        ).strip(),
    }
    experiment_id = digest(identity)
    records = [{**record, "experiment_id": experiment_id} for record in records]
    report = {
        **identity,
        **analysis,
        "experiment_id": experiment_id,
        "claim_label": CLAIM,
        "final_oos_evaluated": False,
        "model_eligible_observations": 0,
        "trajectory_records_sha256": digest(records),
    }
    folder = b.ROOT / ".local-data/research/experiments" / experiment_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    for filename, data in (
        ("research-redesign-trajectories.json", records),
        ("research-redesign-result.json", report),
    ):
        path = folder / filename
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
                "rows": result["trajectory_records"],
                "counts_by_slot": result["state_counts_by_slot"],
                "sensitivity": result["label_sensitivity"],
                "transitions": result["transition_matrix"],
            },
            indent=2,
        )
    )
