"""One remotely deployable, scheduler-free prospective decision capture iteration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.metadata import version

from sessionzero_bitget import BitgetMarketClient
from sessionzero_bitget.client import HISTORY_CANDLES_ENDPOINT
from sessionzero_config import get_settings
from sessionzero_market_data import XnysTradingCalendar, load_bitget_source_session_evidence
from sessionzero_market_data.alpaca import AlpacaNativeEquityProvider
from sessionzero_market_data.source_sessions import CuratedBitgetSourceSessionProvider
from sessionzero_schemas import (
    ProspectiveRetrieval,
    build_decision_snapshot,
    canonical_digest,
)

from .capture import persist_point_in_time_capture
from .dataset_artifacts import load_cohort
from .engine import create_database_engine, verify_database_connection


def utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def validate_capture_window(
    *, decision_timestamp: datetime, now: datetime, lead_minutes: int = 10
) -> None:
    decision, now = utc(decision_timestamp, "decision_timestamp"), utc(now, "now")
    if not decision - timedelta(minutes=lead_minutes) <= now <= decision:
        raise ValueError("capture must start inside the predeclared pre-decision window")


def git_commit() -> str:
    configured = os.getenv("SESSIONZERO_GIT_COMMIT")
    if configured:
        if len(configured) < 7:
            raise ValueError("SESSIONZERO_GIT_COMMIT is invalid")
        return configured
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=True
    ).stdout
    if dirty:
        raise ValueError("capture requires a clean tree or injected SESSIONZERO_GIT_COMMIT")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()


def calendar_identity(session) -> str:
    return canonical_digest(
        {
            "provider": "exchange_calendars",
            "provider_version": version("exchange-calendars"),
            "calendar": "XNYS",
            "session_date": str(session.reference_session_date),
            "regular_open": session.regular_open.isoformat(),
            "regular_close": session.regular_close.isoformat(),
            "previous_cash_close": session.previous_cash_close.isoformat(),
        }
    )


def _reality_retrieval(
    client: BitgetMarketClient,
    *,
    symbol: str,
    decision: datetime,
    commit: str,
) -> ProspectiveRetrieval:
    request_time = datetime.now(UTC)
    response = client.request_public(
        HISTORY_CANDLES_ENDPOINT,
        {
            "category": "SPOT",
            "symbol": symbol,
            "interval": "1H",
            "type": "market",
            "limit": "3",
            "startTime": str(int((decision - timedelta(hours=3)).timestamp() * 1000)),
            "endTime": str(int(decision.timestamp() * 1000)),
        },
    )
    ingestion_time = datetime.now(UTC)
    if not isinstance(response.data, list):
        raise ValueError("Bitget Reality response is not a candle list")
    eligible = [
        row
        for row in response.data
        if isinstance(row, list)
        and len(row) >= 7
        and datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC) + timedelta(hours=1) < decision
    ]
    if not eligible:
        raise ValueError(f"no completed Reality decision mark for {symbol}")
    row = max(eligible, key=lambda item: int(item[0]))
    event_time = datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC)
    values = tuple(Decimal(str(value)) for value in row[1:7])
    open_, high, low, close, volume, turnover = values
    if min(open_, high, low, close) <= 0 or low > min(open_, close) or high < max(open_, close):
        raise ValueError("Bitget Reality candle failed OHLC validation")
    canonical = {
        "interval": "1H",
        "open": str(open_),
        "high": str(high),
        "low": str(low),
        "close": str(close),
        "volume": str(volume),
        "turnover": str(turnover),
    }
    return ProspectiveRetrieval(
        source="bitget",
        symbol=symbol,
        endpoint=HISTORY_CANDLES_ENDPOINT,
        field_name="REALITY_DECISION_MARK",
        event_time=event_time,
        request_time=request_time,
        ingestion_time=ingestion_time,
        provider_identifiers={"requestTime": response.payload["requestTime"]},
        raw_response=response.payload,
        canonical_value=canonical,
        git_commit=commit,
    )


def _native_close_retrieval(
    provider: AlpacaNativeEquityProvider,
    *,
    symbol: str,
    close_time: datetime,
    commit: str,
) -> ProspectiveRetrieval:
    event_time = close_time - timedelta(minutes=1)
    request_time = datetime.now(UTC)
    history = provider.get_candles(symbol, event_time, close_time)
    if len(history.candles) != 1 or len(history.pages) != 1:
        raise ValueError(f"no unique previous native close for {symbol}")
    candle, page = history.candles[0], history.pages[0]
    if candle.event_time != event_time:
        raise ValueError("native close is not the exact final regular minute")
    raw = json.loads(page.body, parse_float=str, parse_int=str)
    canonical = candle.model_dump(mode="json", exclude={"ingestion_time", "page_index"})
    return ProspectiveRetrieval(
        source="alpaca",
        symbol=symbol,
        endpoint=page.endpoint,
        field_name="PREVIOUS_NATIVE_CLOSE",
        event_time=event_time,
        request_time=request_time,
        ingestion_time=page.ingestion_time,
        provider_identifiers={
            key: value
            for key, value in page.headers.items()
            if key in {"x-request-id", "date", "x-ratelimit-limit", "x-ratelimit-remaining"}
        },
        raw_response=raw,
        canonical_value=canonical,
        git_commit=commit,
    )


def capture_iteration(
    *, decision_timestamp: datetime, symbols: tuple[str, ...], lead_minutes: int = 10
) -> dict:
    started = datetime.now(UTC)
    decision = utc(decision_timestamp, "decision_timestamp")
    validate_capture_window(decision_timestamp=decision, now=started, lead_minutes=lead_minutes)
    cohort = load_cohort()
    members = {member.symbol: member for member in cohort.members}
    if not symbols or any(symbol not in members for symbol in symbols):
        raise ValueError("symbols must be a non-empty subset of the frozen cohort")

    calendar = XnysTradingCalendar()
    session = calendar.session_at(decision)
    if session.regular_open - timedelta(hours=1) != decision:
        raise ValueError("decision timestamp must be exactly 60 minutes before XNYS open")
    commit = git_commit()
    retrievals: list[ProspectiveRetrieval] = []
    with BitgetMarketClient() as bitget:
        alpaca = AlpacaNativeEquityProvider(cohort)
        try:
            for symbol in sorted(symbols):
                retrievals.append(
                    _reality_retrieval(bitget, symbol=symbol, decision=decision, commit=commit)
                )
                retrievals.append(
                    _native_close_retrieval(
                        alpaca,
                        symbol=members[symbol].native_ticker,
                        close_time=session.previous_cash_close,
                        commit=commit,
                    )
                )
        finally:
            alpaca.close()
    if any(item.ingestion_time > decision for item in retrievals):
        raise ValueError("capture did not finish collecting observations by decision time")

    source_provider = CuratedBitgetSourceSessionProvider()
    source_evidence = load_bitget_source_session_evidence()
    evidence_by_id = {item.evidence_id: item for item in source_evidence.evidence}
    assessments = {}
    for symbol in sorted(symbols):
        assessment = source_provider.session_at(symbol, decision)
        if assessment.availability.value != "EXPECTED_OPEN":
            raise ValueError("Reality source is not evidenced open at decision time")
        if any(
            evidence_by_id[eid].publication_time is None
            or evidence_by_id[eid].publication_time > decision
            for eid in assessment.evidence_ids
        ):
            raise ValueError("source-session evidence was not available by decision time")
        assessments[symbol] = assessment.model_dump(mode="json")

    calendar_version = calendar_identity(session)
    dataset_version = canonical_digest(
        {
            "contract": "prospective_point_in_time_dataset.v1",
            "mapping_version": cohort.cohort_version,
            "calendar_version": calendar_version,
            "symbols": sorted(symbols),
        }
    )
    snapshot = build_decision_snapshot(
        decision_timestamp=decision,
        retrievals=tuple(retrievals),
        source_session_evidence=assessments,
        source_session_evidence_version=source_evidence.transformation_version,
        calendar_version=calendar_version,
        mapping_version=cohort.cohort_version,
        dataset_version=dataset_version,
    )
    completed = datetime.now(UTC)
    engine = create_database_engine(get_settings().require_database_url())
    try:
        verify_database_connection(engine)
        result = persist_point_in_time_capture(
            engine,
            capture_id=uuid.uuid4(),
            started_at=started,
            completed_at=completed,
            retrievals=tuple(retrievals),
            snapshot=snapshot,
        )
    finally:
        engine.dispose()
    return {
        **result,
        "decision_timestamp": decision.isoformat(),
        "symbols": len(symbols),
        "contains_future_outcome": False,
        "status": "PROSPECTIVELY_SAFE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-timestamp", required=True)
    parser.add_argument("--symbols", help="comma-separated frozen-cohort symbols; default: all 21")
    parser.add_argument("--capture-lead-minutes", type=int, default=10, choices=range(1, 31))
    args = parser.parse_args()
    cohort = load_cohort()
    symbols = (
        tuple(item.strip().upper() for item in args.symbols.split(",") if item.strip())
        if args.symbols
        else tuple(member.symbol for member in cohort.members)
    )
    result = capture_iteration(
        decision_timestamp=datetime.fromisoformat(args.decision_timestamp.replace("Z", "+00:00")),
        symbols=symbols,
        lead_minutes=args.capture_lead_minutes,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
