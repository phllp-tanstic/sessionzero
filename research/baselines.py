"""Frozen non-ML baseline diagnostics. Final OOS is deliberately unsupported."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import statistics
import subprocess
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sessionzero_database.dataset_artifacts import digest
from sessionzero_market_data.source_sessions import (
    CuratedBitgetSourceSessionProvider,
    load_bitget_source_session_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/protocols/baseline-v1.json"
PROTOCOL_SHA256 = "dd76ecabe2386e207608d155ff6f53b5fafa7deba305910bdcc0905f5e11c6ba"
NAMES = ("PREVIOUS_CLOSE", "REALITY_MARK", "REALITY_RETURN_TRANSFER", "SIMPLE_BLEND")


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("UTC timestamp required")
    return result


def partition_bounds(protocol: dict, partition: str) -> tuple[datetime, datetime]:
    if partition not in ("DEVELOPMENT", "VALIDATION"):
        raise ValueError("FINAL_OOS_LOCKED: only DEVELOPMENT and VALIDATION are permitted")
    start, end = map(timestamp, protocol["splits"][partition])
    if end > timestamp(protocol["splits"]["FINAL_OOS"][0]):
        raise ValueError("FINAL_OOS_LOCKED: partition overlaps holdout")
    return start, end


def decision_time(session: dict) -> datetime:
    return timestamp(session["regular_open"]) - timedelta(hours=1)


def in_partition(session: dict, bounds: tuple[datetime, datetime]) -> bool:
    start, end = bounds
    # The label is an OHLC field in a first-minute bar; require the bar to finish.
    return start <= decision_time(session) < timestamp(session["regular_open"]) < end and (
        timestamp(session["regular_open"]) + timedelta(minutes=1) < end
    )


def require_model_eligible(
    protocol: dict, field: str, available_at: datetime | None, decision: datetime
) -> None:
    rule = protocol["eligibility"].get(field, {})
    if (
        rule.get("role") != "AVAILABLE_AT_DECISION_TIME"
        or not rule.get("model_eligible")
        or available_at is None
        or available_at > decision
    ):
        raise ValueError(f"MODEL_FEATURE_FORBIDDEN: {field}")


def predict(previous_close: float, mark: float | None, anchor: float | None) -> dict:
    """Outcome-free scalar interface; research diagnostics only, not feature eligibility."""
    for value in (previous_close, mark, anchor):
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("Prices must be finite and positive")
    transfer = previous_close * mark / anchor if mark is not None and anchor is not None else None
    return dict(
        zip(
            NAMES,
            (
                previous_close,
                mark,
                transfer,
                (previous_close + transfer) / 2 if transfer is not None else None,
            ),
            strict=True,
        )
    )


def metrics(rows: list[tuple[float, float, float]]) -> dict:
    """(prediction, target, previous close); equal observation weights; exact sign ties."""
    if not rows:
        return {"n": 0, "price": None, "bps": None, "directional_accuracy": None}

    def summary(errors):
        return {
            "mae": statistics.mean(map(abs, errors)),
            "rmse": math.sqrt(statistics.mean(x * x for x in errors)),
            "median_absolute_error": statistics.median(map(abs, errors)),
            "signed_bias": statistics.mean(errors),
        }

    def sign(x):
        return (x > 0) - (x < 0)

    return {
        "n": len(rows),
        "price": summary([p - y for p, y, c in rows]),
        "bps": summary([10000 * (p - y) / c for p, y, c in rows]),
        "directional_accuracy": statistics.mean(sign(p - c) == sign(y - c) for p, y, c in rows),
    }


def age_summary(ages: list[float]) -> dict:
    if not ages:
        return {"n": 0}
    values = sorted(ages)
    return {
        "n": len(ages),
        "min_seconds": values[0],
        "median_seconds": statistics.median(values),
        "p95_seconds": values[math.ceil(0.95 * len(values)) - 1],
        "max_seconds": values[-1],
        "over_one_hour": sum(v > 3600 for v in values),
        "exclusion_threshold": None,
    }


def select_mark(
    candles: dict[datetime, float], decision: datetime, previous_close_time: datetime
) -> tuple[float | None, float | None]:
    # Keys are bar COMPLETION times. Do not forward fill from an earlier cash session.
    candidates = [t for t in candles if previous_close_time <= t < decision]
    if not candidates:
        return None, None
    latest = max(candidates)
    return candles[latest], (decision - latest).total_seconds()


def source_path_known(provider, symbol: str, start: datetime, end: datetime) -> bool:
    times = [end]
    current = start - timedelta(hours=1)  # include full reference-anchor bar
    while current < end:
        times.append(current)
        current += timedelta(hours=1)
    for t in times:
        assessment = provider.session_at(symbol, t)
        if assessment.availability.value != "EXPECTED_OPEN":
            return False
        evidence = {r.evidence_id: r for r in provider.evidence}
        if not assessment.evidence_ids or any(
            evidence[eid].publication_time is None or evidence[eid].publication_time > t
            for eid in assessment.evidence_ids
        ):
            return False
    return True


def load_contract() -> tuple[dict, dict, dict]:
    raw_protocol = PROTOCOL.read_bytes()
    if hashlib.sha256(raw_protocol).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("Frozen protocol changed; create a new version")
    protocol = json.loads(raw_protocol)
    metadata = ROOT / "datasets/phase1"
    version = json.loads((metadata / "latest.json").read_text())["dataset_version"]
    if version != protocol["dataset_version"]:
        raise ValueError("Frozen dataset pointer changed")
    raw = (metadata / f"{version}.json").read_bytes()
    manifest = json.loads(raw)
    if hashlib.sha256(raw).hexdigest() != protocol["dataset_manifest_sha256"]:
        raise ValueError("Frozen manifest changed")
    if digest(manifest["identity"]) != version:
        raise ValueError("Dataset identity mismatch")
    calendar = json.loads((metadata / "calendar.json").read_text())
    payload = {k: v for k, v in calendar.items() if k != "calendar_version"}
    if digest(payload) != manifest["identity"]["calendar_version"]:
        raise ValueError("Calendar identity mismatch")
    evidence = load_bitget_source_session_evidence()
    if (
        digest(evidence.model_dump(mode="json"))
        != manifest["identity"]["session_evidence_content_version"]
    ):
        raise ValueError("Session evidence identity mismatch")
    return protocol, manifest, calendar


def read_archive(manifest: dict, filename: str) -> dict:
    archive = manifest["archives"]
    path = ROOT / archive["root"] / archive["directory"] / filename
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != archive["sha256"][filename]:
        raise ValueError(f"Archive checksum mismatch: {filename}")
    return json.loads(raw)


def native_price(row: dict | None, leg: str, expected_time: datetime) -> float | None:
    if row is None or row[leg]["status"] != "AVAILABLE":
        return None
    candles = row[leg]["history"]["candles"]
    if len(candles) != 1 or timestamp(candles[0]["event_time"]) != expected_time:
        raise ValueError("Not an exact native boundary minute")
    return float(candles[0][leg])


def evaluate(protocol: dict, manifest: dict, calendar: dict, partition: str) -> dict:
    bounds = partition_bounds(protocol, partition)  # BEFORE archive reads or outcome access
    provider = CuratedBitgetSourceSessionProvider()
    sessions = calendar["sessions"]
    selected = [
        (previous, session)
        for previous, session in itertools.pairwise(sessions)
        if session["role"] == "EVALUATION" and in_partition(session, bounds)
    ]
    samples = {name: [] for name in NAMES}
    common = {name: [] for name in NAMES}
    excluded = {name: Counter() for name in NAMES}
    symbol_counts = {}
    ages, records = [], []
    for member in manifest["identity"]["members"]:
        symbol = member["symbol"]
        # Decode the immutable archive, but select temporal scope before reading price fields.
        native = {
            r["session"]["session_date"]: r
            for r in read_archive(manifest, f"native-{symbol}.json")["rows"]
            if timestamp(r["session"]["regular_open"]) < bounds[1]
        }
        reality = {}
        for observation in read_archive(manifest, f"reality-{symbol}.json")["observations"]:
            candle = observation["candle"]
            completion = timestamp(candle["event_time"]) + timedelta(hours=1)
            if completion < bounds[1]:
                if completion in reality:
                    raise ValueError("Duplicate Reality observation")
                reality[completion] = float(candle["close"])
        symbol_counts[symbol] = {name: 0 for name in NAMES}
        for previous, session in selected:
            decision = decision_time(session)
            close_time = timestamp(previous["regular_close"])
            close = native_price(
                native.get(previous["session_date"]), "close", close_time - timedelta(minutes=1)
            )
            mark, age = select_mark(reality, decision, close_time)
            if age is not None:
                ages.append(age)
            anchor = reality.get(close_time)
            known = source_path_known(provider, symbol, close_time, decision)
            if not known:
                mark, anchor = None, None
            forecasts = predict(close, mark, anchor) if close is not None else dict.fromkeys(NAMES)
            # Forecasts have been computed before the separate outcome leg is read.
            target = native_price(
                native.get(session["session_date"]), "open", timestamp(session["regular_open"])
            )
            all_present = target is not None and all(v is not None for v in forecasts.values())
            record = {
                "symbol": symbol,
                "decision_time": decision.isoformat(),
                "outcome_time": session["regular_open"],
                "age_seconds": age,
                "predictions": forecasts,
                "target": target,
                "previous_close": close,
                "source_path_known": known,
                "missing_reality_intervals": sum(
                    close_time <= t < decision and t not in reality
                    for t in (
                        close_time + timedelta(hours=h)
                        for h in range(int((decision - close_time).total_seconds() // 3600) + 1)
                    )
                ),
            }
            records.append(record)
            for name, forecast in forecasts.items():
                if close is None or target is None:
                    excluded[name]["NATIVE_BOUNDARY_MISSING"] += 1
                elif forecast is None:
                    reason = (
                        "SOURCE_PATH_UNKNOWN_OR_CLOSED"
                        if not known
                        else "REALITY_MARK_MISSING"
                        if mark is None
                        else "EXACT_ANCHOR_MISSING"
                    )
                    excluded[name][reason] += 1
                else:
                    row = (forecast, target, close)
                    samples[name].append(row)
                    symbol_counts[symbol][name] += 1
                    if all_present:
                        common[name].append(row)
    return {
        "partition": partition,
        "claim_label": "ESTIMATED",
        "mode": "RETROSPECTIVE_EVENT_TIME_DIAGNOSTIC",
        "model_eligible_observations": 0,
        "symbols_in_scope": len(symbol_counts),
        "symbol_observation_counts": symbol_counts,
        "candidate_observations": len(records),
        "decision_timestamps": sorted({r["decision_time"] for r in records}),
        "metrics": {name: metrics(rows) for name, rows in samples.items()},
        "common_sample_metrics": {name: metrics(rows) for name, rows in common.items()},
        "excluded": {name: dict(counts) for name, counts in excluded.items()},
        "missing_reality_intervals": sum(r["missing_reality_intervals"] for r in records),
        "staleness": age_summary(ages),
        "records": records,
    }


def experiment_identity(protocol: dict, code_hashes: dict, partition: str) -> dict:
    partition_bounds(protocol, partition)
    return {
        "dataset_version": protocol["dataset_version"],
        "protocol_sha256": digest(protocol),
        "split_version": protocol["split_version"],
        "feature_set_version": protocol["feature_set_version"],
        "target_version": protocol["target_version"],
        "partition": partition,
        "code_hashes": code_hashes,
        "parameters": protocol["parameters"],
        "random_seed": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition", choices=("DEVELOPMENT", "VALIDATION"), default="DEVELOPMENT")
    args = parser.parse_args()
    protocol, manifest, calendar = load_contract()
    hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "research").glob("*.py"))
    }
    # Bind imported data-plane source too, without changing accepted dataset files.
    for relative in manifest["identity"]["source_file_hashes"]:
        hashes[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    identity = experiment_identity(protocol, hashes, args.partition)
    experiment_id = digest(identity)
    result = evaluate(protocol, manifest, calendar, args.partition)
    records = result.pop("records")
    report = {
        **result,
        **identity,
        "experiment_id": experiment_id,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_commit_semantics": "BASE_COMMIT_PLUS_EXACT_SOURCE_HASHES",
        "timestamp": datetime.now(UTC).isoformat(),
        "final_oos_evaluated": False,
        "limitation": protocol["diagnostic_permission"]["assumption"],
        "records_sha256": digest(records),
    }
    # Private, append-only per-experiment registry. No prices/derived results in public routes.
    directory = ROOT / ".local-data/research/experiments" / experiment_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "result.json"
    if path.exists():
        old = json.loads(path.read_text())

        def stable(r):
            return {k: v for k, v in r.items() if k not in ("timestamp", "git_commit")}

        if stable(old) != stable(report):
            raise ValueError("Non-reproducible experiment; existing result preserved")
    else:
        for filename, data in (("records.json", records), ("result.json", report)):
            fd = os.open(directory / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
    print(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "report": str(path),
                "candidate_observations": result["candidate_observations"],
                "metrics": result["metrics"],
                "excluded": result["excluded"],
                "staleness": result["staleness"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
