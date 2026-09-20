"""Materialize immutable target versions and explicit outcome joins from retained evidence."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from sessionzero_bitget import CandleObservation
from sessionzero_market_data import XnysTradingCalendar, load_bitget_source_session_evidence
from sessionzero_market_data.alpaca import SAFE_HEADERS, AlpacaNativeEquityProvider
from sessionzero_market_data.native import NativeDataError
from sessionzero_schemas import MarketCandle
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .dataset_artifacts import (
    STATUSES,
    TARGET_DEFINITION,
    TRANSFORMATION,
    decode_history,
    digest,
    pair_status,
    target_date,
)
from .models import (
    IngestionRun,
    NativeSessionTarget,
    NormalizedMarketCandle,
    Phase1DatasetManifest,
    Phase1DatasetReality,
    Phase1DatasetTarget,
    RawMarketObservation,
)
from .native import native_candle_version, persist_native_history
from .persistence import ingest_candle_observations

PIT_POLICY = {
    "next_open_role": "FUTURE_OUTCOME",
    "previous_close_role": "CONTEXT_AVAILABILITY_UNVERIFIED",
    "reality_role": "OBSERVED_HISTORY_NOT_AS_KNOWN",
    "decision_timestamp": "REALITY_BAR_START_PLUS_1H",
    "native_price_basis": "RAW_EVENT_TIME_NO_CORPORATE_ACTION_RESTATEMENT",
    "historical_original_availability": "NOT_CLAIMED",
    "feature_use": "PROHIBITED_WITHOUT_PHASE2_AVAILABILITY_POLICY",
}


def prepare_target(row: dict, cohort, calendar: dict) -> tuple[dict, dict]:
    """No nearest-minute replacement. Validate identity, calendar and both exact boundaries."""
    member = next((m for m in cohort.members if m.symbol == row["reality_symbol"]), None)
    s = row["session"]
    if (
        member is None
        or member.native_ticker != row["native_ticker"]
        or s not in calendar["sessions"]
    ):
        raise NativeDataError("TARGET_COHORT_OR_CALENDAR_MISMATCH")
    opening, closing = (
        datetime.fromisoformat(s["regular_open"]),
        datetime.fromisoformat(s["regular_close"]),
    )
    histories = {}
    identity = {
        "cohort_version": cohort.cohort_version,
        "universe_version": cohort.universe_version,
        "reality_symbol": member.symbol,
        "native_ticker": member.native_ticker,
        "session_date": s["session_date"],
        "regular_open": s["regular_open"],
        "regular_close": s["regular_close"],
        "calendar_version": calendar["calendar_version"],
        "calendar_provider": calendar["provider"],
        "calendar_provider_version": calendar["provider_version"],
        "source": "alpaca",
        "feed": "sip",
        "adjustment": "raw",
        "interval": "1Min",
        "target_definition_version": TARGET_DEFINITION,
        "transformation_version": TRANSFORMATION,
        "open_definition": "FIRST_1M_BAR_OPEN",
        "close_definition": "LAST_1M_BAR_CLOSE",
    }
    for leg, expected in (("open", opening), ("close", closing - timedelta(minutes=1))):
        value = row[leg]
        identity[leg] = {
            "status": value["status"],
            "candle_version": None,
            "error_code": value.get("error_code"),
        }
        if "history" not in value:
            if value["status"] not in ("PROVIDER_FAILURE", "STRUCTURAL_FAILURE", "UNKNOWN"):
                raise NativeDataError("TARGET_HISTORY_REQUIRED")
            continue
        history = decode_history(value["history"])
        instrument = history.instrument
        if (
            instrument.reality_symbol != member.symbol
            or instrument.native_ticker != member.native_ticker
            or instrument.cohort_version != cohort.cohort_version
            or instrument.universe_version != cohort.universe_version
            or history.source != "alpaca"
            or history.start != expected
            or history.end != expected + timedelta(minutes=1)
            or not history.pages
            or len(history.candles) > 1
        ):
            raise NativeDataError("TARGET_HISTORY_LINEAGE_OR_BOUNDARY_MISMATCH")
        for page in history.pages:
            if set(page.response_headers) - set(SAFE_HEADERS):
                raise NativeDataError("UNSAFE_NATIVE_PROVENANCE_HEADER")
            if any(
                page.params.get(k) != v
                for k, v in (
                    ("feed", "sip"),
                    ("adjustment", "raw"),
                    ("timeframe", "1Min"),
                    ("asof", "-"),
                )
            ):
                raise NativeDataError("TARGET_SOURCE_CONTRACT_MISMATCH")
        for candle in history.candles:
            if (
                candle.event_time != expected
                or candle.session_date != target_date(s["session_date"])
                or candle.native_ticker != member.native_ticker
                or candle.source != history.source
                or candle.feed != "sip"
                or candle.adjustment != "raw"
            ):
                raise NativeDataError("TARGET_MINUTE_CONTRACT_MISMATCH")
            identity[leg]["candle_version"] = native_candle_version(candle)
        expected_status = "AVAILABLE" if history.candles else "MISSING_BOUNDARY_MINUTE"
        if value["status"] != expected_status:
            raise NativeDataError("TARGET_STATUS_CONTENT_MISMATCH")
        # An explicitly disconnected transport keeps restore independent of credentials/network.
        with_replay = AlpacaNativeEquityProvider(
            cohort,
            transport=httpx.MockTransport(lambda _: httpx.Response(500)),
            page_limit=history.pages[0].params["limit"],
        )
        try:
            with_replay.replay_history(history)
        finally:
            with_replay.close()
        histories[leg] = history
    identity["status"] = pair_status(row["open"]["status"], row["close"]["status"])
    return identity, histories


def persist_target(engine, row: dict, cohort, calendar: dict, *, captured_at: datetime) -> str:
    identity, histories = prepare_target(row, cohort, calendar)
    target_version = digest(identity)
    with engine.connect() as connection:
        if connection.scalar(
            select(NativeSessionTarget.target_version).where(
                NativeSessionTarget.target_version == target_version
            )
        ):
            return target_version
    values = {
        k: identity[k]
        for k in (
            "cohort_version",
            "native_ticker",
            "source",
            "feed",
            "adjustment",
            "calendar_version",
            "transformation_version",
            "target_definition_version",
            "status",
        )
    }
    values.update(
        target_version=target_version,
        session_date=target_date(identity["session_date"]),
        regular_open=datetime.fromisoformat(identity["regular_open"]),
        regular_close=datetime.fromisoformat(identity["regular_close"]),
    )
    ingestion_times = []
    lineage = {}
    for leg in ("open", "close"):
        values.update(
            {
                f"{leg}_{suffix}": None
                for suffix in ("target", "observation_time", "raw_id", "candle_id", "run_id")
            }
        )
        history = histories.get(leg)
        if history is None:
            run_id = uuid.uuid4()
            occurred = (
                datetime.fromisoformat(row[leg]["attempted_at"])
                if "attempted_at" in row[leg]
                else captured_at
            )
            with engine.begin() as connection:
                connection.execute(
                    pg_insert(IngestionRun).values(
                        run_id=run_id,
                        provider=identity["source"],
                        operation="native_session_target_failure",
                        started_at=occurred,
                        finished_at=occurred,
                        status="FAILED",
                        records_received=0,
                        records_written=0,
                        error_code=row[leg].get("error_code", "TARGET_UNKNOWN"),
                    )
                )
            values[f"{leg}_run_id"] = run_id
            ingestion_times.append(occurred)
            continue
        ref = persist_native_history(engine, history)
        values[f"{leg}_run_id"] = uuid.UUID(ref["run_id"])
        values[f"{leg}_raw_id"] = ref["raw_page_ids"][0]
        ingestion_times.extend(p.ingestion_time for p in history.pages)
        lineage[leg] = {
            "raw_page_ids": ref["raw_page_ids"],
            "request_ids": [p.response_headers.get("x-request-id") for p in history.pages],
        }
        if history.candles:
            candle = history.candles[0]
            values[f"{leg}_target"] = candle.open if leg == "open" else candle.close
            values[f"{leg}_observation_time"] = candle.event_time
            values[f"{leg}_raw_id"] = ref["raw_page_ids"][candle.page_index]
            values[f"{leg}_candle_id"] = ref["candles"][0]["normalized_id"]
    values.update(
        ingestion_time=max(ingestion_times), provenance={"identity": identity, "lineage": lineage}
    )
    with engine.begin() as connection:
        connection.execute(pg_insert(NativeSessionTarget).values(**values).on_conflict_do_nothing())
    return target_version


def join_context(event_time: datetime, calendar: XnysTradingCalendar) -> dict:
    decision = event_time + timedelta(hours=1)
    session = calendar.session_at(decision)
    if session.previous_cash_close > decision or session.next_cash_open <= decision:
        raise NativeDataError("CALENDAR_OUTCOME_TIME_ORDER")
    return {
        "decision_time": decision,
        "previous_date": session.previous_cash_close.date(),
        "next_date": session.next_cash_open.date(),
        "cash_market_open": session.cash_market_open,
    }


def reality_identity(candle) -> dict:
    values = candle.model_dump(mode="json", exclude={"ingestion_time"})
    for field in ("open", "high", "low", "close", "volume", "turnover"):
        if values[field] is not None:
            values[field] = format(Decimal(values[field]).normalize(), "f")
    return values


def materialize(
    engine, cohort, calendar: dict, archive_dir: Path, *, code_provenance: dict
) -> tuple[dict, list, list]:
    """Every expected pair is materialized, including missing/failure rows; gate is separate."""
    captured_at = datetime.fromisoformat(
        json.loads((archive_dir / "collection.json").read_text())["finished_at"]
    )
    target_links, reality_links, target_versions, reality_versions = [], [], {}, {}
    per_symbol = []
    aggregate = Counter({s: 0 for s in STATUSES})
    anchor_counts = aggregate.copy()
    native_telemetry = Counter()
    calendar_provider = XnysTradingCalendar()
    unresolved = []
    join_availability = Counter(
        {
            "previous_close_unavailable": 0,
            "next_open_unavailable": 0,
            "off_session_observations": 0,
        }
    )
    expected_sessions = [s for s in calendar["sessions"] if s["role"] == "EVALUATION"]
    for member in cohort.members:
        native = json.loads((archive_dir / f"native-{member.symbol}.json").read_text())
        rows = native["rows"]
        if [r["session"] for r in rows] != calendar["sessions"]:
            raise NativeDataError("INCOMPLETE_OR_DUPLICATE_SYMBOL_SESSIONS")
        counts = Counter({s: 0 for s in STATUSES})
        native_telemetry.update(native["telemetry"])
        lookup = {}
        target_statuses = {}
        for row in rows:
            identity, _ = prepare_target(row, cohort, calendar)
            v = persist_target(engine, row, cohort, calendar, captured_at=captured_at)
            day = target_date(row["session"]["session_date"])
            lookup[day] = v
            target_statuses[day] = identity
            target_versions[f"{member.symbol}/{day}"] = v
            target_links.append(
                {
                    "reality_symbol": member.symbol,
                    "session_date": day,
                    "target_version": v,
                    "session_role": row["session"]["role"],
                }
            )
            if row["session"]["role"] == "EVALUATION":
                counts[identity["status"]] += 1
                aggregate[identity["status"]] += 1
            else:
                anchor_counts[identity["status"]] += 1
        reality = json.loads((archive_dir / f"reality-{member.symbol}.json").read_text())
        observations = tuple(
            CandleObservation(MarketCandle.model_validate(o["candle"]), o["payload"], o["endpoint"])
            for o in reality["observations"]
        )
        quality = reality["quality"]
        if not observations or quality["structural_quality_status"] != "PASS":
            raise NativeDataError("REALITY_STRUCTURAL_FAILURE_OR_EMPTY")
        times = [o.candle.event_time for o in observations]
        if (
            len(set(times)) != len(times)
            or times != sorted(times)
            or any(
                o.candle.symbol != member.symbol
                or o.candle.interval != "1H"
                or not cohort.evaluation_start <= o.candle.event_time < cohort.evaluation_end
                for o in observations
            )
        ):
            raise NativeDataError("REALITY_IDENTITY_OR_WINDOW_MISMATCH")
        reality_versions[member.symbol] = digest([reality_identity(o.candle) for o in observations])
        run = ingest_candle_observations(
            engine,
            observations,
            operation="phase1_dataset_reality",
            interval="1H",
            requested_start=cohort.evaluation_start,
            requested_end=cohort.evaluation_end,
            pages_requested=quality["page_count"],
            quality_status=quality["quality_status"],
        )
        with engine.connect() as connection:
            persisted = (
                connection.execute(
                    select(NormalizedMarketCandle).where(
                        NormalizedMarketCandle.source == observations[0].candle.source,
                        NormalizedMarketCandle.symbol == member.symbol,
                        NormalizedMarketCandle.market == observations[0].candle.market,
                        NormalizedMarketCandle.interval == "1H",
                        NormalizedMarketCandle.event_time >= cohort.evaluation_start,
                        NormalizedMarketCandle.event_time < cohort.evaluation_end,
                    )
                )
                .mappings()
                .all()
            )
            raw = dict(
                connection.execute(
                    select(RawMarketObservation.event_time, RawMarketObservation.id).where(
                        RawMarketObservation.run_id == run.run_id
                    )
                ).all()
            )
        canonical = {r["event_time"]: r for r in persisted}
        member_unresolved = 0
        for observation in observations:
            candle = observation.candle
            stored = canonical[candle.event_time]
            if any(
                stored[k] != getattr(candle, k)
                for k in ("open", "high", "low", "close", "volume", "turnover")
            ):
                raise NativeDataError("REALITY_CANONICAL_REVISION_CONFLICT")
            context = join_context(candle.event_time, calendar_provider)
            join_availability["off_session_observations"] += not context["cash_market_open"]
            previous, following = (
                lookup.get(context["previous_date"]),
                lookup.get(context["next_date"]),
            )
            if previous is None or following is None:
                unresolved.append(
                    {
                        "symbol": member.symbol,
                        "event_time": candle.event_time.isoformat(),
                        "reason": "TARGET_SESSION_NOT_MATERIALIZED",
                    }
                )
                member_unresolved += 1
                continue
            join_availability["previous_close_unavailable"] += (
                target_statuses[context["previous_date"]]["close"]["status"] != "AVAILABLE"
            )
            join_availability["next_open_unavailable"] += (
                target_statuses[context["next_date"]]["open"]["status"] != "AVAILABLE"
            )
            reality_links.append(
                {
                    "candle_id": stored["id"],
                    "raw_observation_id": raw[candle.event_time],
                    "native_ticker": member.native_ticker,
                    "calendar_version": calendar["calendar_version"],
                    "decision_time": context["decision_time"],
                    "previous_close_target_version": previous,
                    "next_open_target_version": following,
                    **{
                        k: PIT_POLICY[k]
                        for k in ("next_open_role", "previous_close_role", "reality_role")
                    },
                }
            )
        oos = cohort.evaluation_end - timedelta(days=30)
        duration_days = (times[-1] + timedelta(hours=1) - times[0]).total_seconds() / 86400
        duration_ok = duration_days >= 60 and times[0] < oos and times[-1] >= oos
        per_symbol.append(
            {
                "reality_symbol": member.symbol,
                "native_ticker": member.native_ticker,
                "sessions_expected": len(expected_sessions),
                "statuses": dict(counts),
                "coverage_percentage": round(
                    100 * counts["TARGET_AVAILABLE"] / len(expected_sessions), 4
                ),
                "reality_observations": len(observations),
                "reality_observed_start": times[0].isoformat(),
                "reality_observed_end": times[-1].isoformat(),
                "reality_duration_days": round(duration_days, 6),
                "duration_and_oos_gate": duration_ok,
                "unresolved_joins": member_unresolved,
                "reality_quality": quality,
            }
        )
        print(
            json.dumps(
                {
                    "stage": "persisted",
                    "symbol": member.symbol,
                    "target_pairs": len(rows),
                    "reality_rows": len(observations),
                }
            ),
            flush=True,
        )
    identity = {
        "transformation_version": TRANSFORMATION,
        "target_definition_version": TARGET_DEFINITION,
        "universe_version": cohort.universe_version,
        "cohort_version": cohort.cohort_version,
        "members": [m.model_dump(mode="json") for m in cohort.members],
        "requested_window": [
            cohort.evaluation_start.isoformat(),
            cohort.evaluation_end.isoformat(),
        ],
        "final_oos_window": [
            (cohort.evaluation_end - timedelta(days=30)).isoformat(),
            cohort.evaluation_end.isoformat(),
        ],
        "intervals": {"reality": "1H", "native": "1Min"},
        "feed": "sip",
        "adjustment": "raw",
        "calendar_version": calendar["calendar_version"],
        "session_evidence_version": cohort.source_session_evidence_version,
        "session_evidence_content_version": digest(
            load_bitget_source_session_evidence().model_dump(mode="json")
        ),
        "reality_transformation_version": "reality_historical_coverage.v4",
        "native_candle_transformation_version": "native_equity_minute.v1",
        "reality_data_version": digest(reality_versions),
        "reality_member_versions": reality_versions,
        "native_target_version": digest(target_versions),
        "native_target_versions": target_versions,
        "point_in_time_policy": PIT_POLICY,
        **code_provenance,
    }
    accepted = (
        not unresolved
        and all(
            p["duration_and_oos_gate"] and p["statuses"]["TARGET_AVAILABLE"] > 0 for p in per_symbol
        )
        and not any(
            aggregate[s] + anchor_counts[s]
            for s in ("PROVIDER_FAILURE", "STRUCTURAL_FAILURE", "UNKNOWN")
        )
    )
    manifest = {
        "dataset_version": digest(identity),
        "identity": identity,
        "generated_at": datetime.now(UTC).isoformat(),
        "phase1_exit": "YES" if accepted else "NO",
        "summary": {
            "evaluation_sessions": len(expected_sessions),
            "evaluation_symbol_session_pairs": len(expected_sessions) * len(cohort.members),
            "evaluation_statuses": dict(aggregate),
            "anchor_statuses": dict(anchor_counts),
            "all_target_pairs": len(target_links),
            "reality_rows": len(reality_links),
            "native_telemetry": dict(native_telemetry),
            "unresolved_joins": unresolved,
            "join_availability": dict(join_availability),
            "per_symbol": per_symbol,
        },
    }
    return manifest, target_links, reality_links


def persist_manifest(engine, manifest: dict, target_links: list, reality_links: list) -> None:
    version = manifest["dataset_version"]
    if version != digest(manifest["identity"]):
        raise NativeDataError("DATASET_MANIFEST_HASH_MISMATCH")
    with engine.begin() as connection:
        connection.execute(
            pg_insert(Phase1DatasetManifest)
            .values(
                dataset_version=version,
                manifest=manifest,
                generated_at=datetime.fromisoformat(manifest["generated_at"]),
            )
            .on_conflict_do_nothing()
        )
        for model, rows in (
            (Phase1DatasetTarget, target_links),
            (Phase1DatasetReality, reality_links),
        ):
            for offset in range(0, len(rows), 500):
                connection.execute(
                    pg_insert(model)
                    .values(
                        [{**r, "dataset_version": version} for r in rows[offset : offset + 500]]
                    )
                    .on_conflict_do_nothing()
                )
