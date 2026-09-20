"""Bounded private verification only. Writes raw evidence to a mode-0600 local report."""

from __future__ import annotations

import argparse
import json
import os
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sessionzero_bitget import (
    BitgetMarketClient,
    BitgetProviderError,
    BitgetReferenceDataProvider,
    derive_evidence_qualified_cohort,
)
from sessionzero_config import get_settings
from sessionzero_market_data import XnysTradingCalendar, load_bitget_source_session_evidence
from sessionzero_market_data.alpaca import native_provider
from sessionzero_market_data.native import NativeDataError
from sqlalchemy.exc import SQLAlchemyError

from .coverage import load_accepted_universe
from .engine import create_database_engine
from .native import persist_native_history
from .native_cohort import reverify_native_cohort


def probe(provider, cohort, *, engine=None) -> dict:
    calendar = XnysTradingCalendar()
    sessions = []
    day = cohort.evaluation_start.date() + timedelta(days=1)
    while day < cohort.evaluation_end.date():
        with suppress(ValueError):
            sessions.append(calendar.session_on(day))
        day += timedelta(days=1)
    selected = [sessions[i * (len(sessions) - 1) // 4] for i in range(5)]
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "cohort": cohort.model_dump(mode="json"),
        "feed": "sip",
        "adjustment": "raw",
        "private_use": "PROVISIONAL",
        "public_raw_display": "NOT_APPROVED",
        "public_derived_outputs": "UNVERIFIED",
        "pilot": [],
        "availability": [],
        "target_pairs": [],
        "histories": [],
    }

    def retain(history):
        value = asdict(history)
        value["instrument"] = history.instrument.model_dump(mode="json")
        value["candles"] = [c.model_dump(mode="json") for c in history.candles]
        if engine is not None:
            value["persistence"] = persist_native_history(engine, history)
        report["histories"].append(value)

    # Fixed native tickers locate accepted mappings; never infer a Reality symbol.
    provider.page_limit = 2
    for ticker in ("AAPL", "NVDA", "TSLA"):
        member = next((m for m in cohort.members if m.native_ticker == ticker), None)
        entry = {"native_ticker": ticker}
        try:
            if member is None:
                raise NativeDataError("PILOT_NOT_IN_ACCEPTED_COHORT")
            history = provider.get_candles(
                member.symbol,
                selected[0].regular_open,
                selected[0].regular_open + timedelta(minutes=5),
            )
            retain(history)
            entry.update(
                status="AVAILABLE" if history.candles else "EMPTY_VALID_HISTORY",
                pages=len(history.pages),
                bars=len(history.candles),
                pagination_verified=len(history.pages) > 1,
                timestamps=[c.event_time.isoformat() for c in history.candles],
            )
        except NativeDataError as exc:
            entry.update(status=exc.state.value, error=exc.code)
        report["pilot"].append(entry)
    provider.page_limit = 10000
    for member in cohort.members:
        entry = {"reality_symbol": member.symbol, "native_ticker": member.native_ticker}
        try:
            opening = provider.get_session_open(member.symbol, selected[0].reference_session_date)
            retain(opening.history)
            closing = provider.get_session_close(member.symbol, selected[0].reference_session_date)
            retain(closing.history)
            entry.update(
                open_status=opening.status,
                close_status=closing.status,
                status="AVAILABLE" if opening.price and closing.price else "MISSING_TARGET",
            )
        except NativeDataError as exc:
            entry.update(status=exc.state.value, error=exc.code)
        report["availability"].append(entry)
    for member in cohort.members[:5]:
        for session in selected:
            entry = {
                "reality_symbol": member.symbol,
                "native_ticker": member.native_ticker,
                "cash_session_date": str(session.reference_session_date),
                "regular_open_utc": session.regular_open.isoformat(),
                "regular_close_utc": session.regular_close.isoformat(),
                "source": "alpaca",
                "feed": "sip",
                "adjustment": "raw",
            }
            try:
                next_date = calendar.session_at(session.next_cash_open).reference_session_date
                for name, method, target_date in (
                    ("opening", provider.get_session_open, session.reference_session_date),
                    ("closing", provider.get_session_close, session.reference_session_date),
                    ("next_opening", provider.get_session_open, next_date),
                ):
                    target = method(member.symbol, target_date)
                    retain(target.history)
                    entry[name] = {
                        "price": str(target.price) if target.price is not None else None,
                        "status": target.status,
                        "definition": target.definition,
                        "session_date": str(target.session_date),
                    }
                entry["status"] = (
                    "AVAILABLE"
                    if all(
                        entry[k]["status"] == "AVAILABLE"
                        for k in ("opening", "closing", "next_opening")
                    )
                    else "MISSING_TARGET"
                )
            except NativeDataError as exc:
                entry.update(status=exc.state.value, error=exc.code)
            report["target_pairs"].append(entry)
    report["telemetry"] = provider.telemetry
    report["request_attempts"] = provider.attempts
    report["accepted"] = (
        all(e.get("pagination_verified") for e in report["pilot"])
        and all(e["status"] == "AVAILABLE" for e in report["availability"])
        and all(e["status"] == "AVAILABLE" for e in report["target_pairs"])
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-version", required=True)
    parser.add_argument("--cohort-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--persist", action="store_true")
    parser.add_argument(
        "--evidence-record", help="Reverify membership and mappings without a snapshot DB"
    )
    args = parser.parse_args()
    engine = provider = None
    try:
        if not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"):
            raise NativeDataError("MISSING_ALPACA_CREDENTIALS")
        mapping_raw = ()
        if args.evidence_record:
            with BitgetMarketClient() as bitget:
                cohort, mapping_raw = reverify_native_cohort(
                    BitgetReferenceDataProvider(bitget),
                    evidence_id=args.evidence_record,
                    original_universe_version=args.universe_version,
                    expected_cohort_version=args.cohort_version,
                )
            if args.persist:
                engine = create_database_engine(get_settings().require_database_url())
        else:
            engine = create_database_engine(get_settings().require_database_url())
            universe = load_accepted_universe(engine, args.universe_version)
            cohort = derive_evidence_qualified_cohort(
                universe_version=universe.universe_version,
                universe_members=universe.members,
                evidence_dataset=load_bitget_source_session_evidence(),
            )
        if cohort.cohort_version != args.cohort_version or len(cohort.members) != 21:
            raise NativeDataError("ACCEPTED_21_COHORT_MISMATCH")
        provider = native_provider(cohort)
        report = probe(provider, cohort, engine=engine if args.persist else None)
        report["mapping_raw_evidence"] = [asdict(r) for r in mapping_raw]
        report["cohort_verification_mode"] = (
            "EVIDENCE_AND_LIVE_MAPPING_HASH_REVERIFIED"
            if args.evidence_record
            else "ACCEPTED_PERSISTED_UNIVERSE"
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Refuse overwrite/symlinks; private report includes raw prices and must stay local.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(report, output, default=str, indent=2)
            output.write("\n")
        print(
            json.dumps(
                {
                    "accepted": report["accepted"],
                    "pilot_symbols": len(report["pilot"]),
                    "cohort_symbols": len(report["availability"]),
                    "target_pairs": len(report["target_pairs"]),
                    "telemetry": report["telemetry"],
                }
            )
        )
        if not report["accepted"]:
            raise SystemExit(1)
    except (NativeDataError, BitgetProviderError, ValueError, SQLAlchemyError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "GATED" if not provider else "UNAVAILABLE",
                    "details": exc.details if isinstance(exc, NativeDataError) else {},
                    "error": exc.code
                    if isinstance(exc, NativeDataError)
                    else "VERIFICATION_CONFIGURATION_OR_STORAGE_FAILURE",
                }
            )
        )
        raise SystemExit(1) from None
    finally:
        if provider is not None:
            provider.close()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
