"""Synthetic minute prices for dataset contract tests; never production evidence."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sessionzero_database.dataset_artifacts import calendar_artifact, encode_history, load_cohort
from sessionzero_market_data.native import NativeCandle, NativeHistory, NativeInstrument, NativePage


@pytest.fixture
def phase1_fixture():
    cohort = load_cohort()
    calendar = calendar_artifact(cohort)
    captured = datetime(2026, 9, 20, tzinfo=UTC)
    member = cohort.members[0]
    instrument = NativeInstrument(
        reality_symbol=member.symbol,
        native_ticker=member.native_ticker,
        universe_version=cohort.universe_version,
        cohort_version=cohort.cohort_version,
    )

    def row(session=None, *, missing=()):
        session = session or calendar["sessions"][1]
        result = {
            "reality_symbol": member.symbol,
            "native_ticker": member.native_ticker,
            "session": session,
        }
        for leg in ("open", "close"):
            event = datetime.fromisoformat(session[f"regular_{leg}"])
            if leg == "close":
                event -= timedelta(minutes=1)
            candle = NativeCandle(
                source="alpaca",
                native_ticker=member.native_ticker,
                feed="sip",
                event_time=event,
                ingestion_time=captured,
                session_date=event.date(),
                open=100,
                high=102,
                low=99,
                close=101,
                volume=10,
                trade_count=2,
                page_index=0,
            )
            page = NativePage(
                f"https://data.alpaca.markets/v2/stocks/{member.native_ticker}/bars",
                {
                    "feed": "sip",
                    "adjustment": "raw",
                    "timeframe": "1Min",
                    "asof": "-",
                    "start": event.isoformat(),
                    "end": (event + timedelta(minutes=1)).isoformat(),
                    "sort": "asc",
                    "limit": 10000,
                },
                captured,
                {"x-request-id": "SYNTHETIC_TEST"},
                json.dumps(
                    {
                        "symbol": member.native_ticker,
                        "next_page_token": None,
                        "bars": []
                        if leg in missing
                        else [
                            {
                                "t": event.isoformat(),
                                "o": 100,
                                "h": 102,
                                "l": 99,
                                "c": 101,
                                "v": 10,
                                "n": 2,
                            }
                        ],
                    }
                ),
            )
            history = NativeHistory(
                instrument,
                event,
                event + timedelta(minutes=1),
                (page,),
                () if leg in missing else (candle,),
                "alpaca",
            )
            result[leg] = {
                "status": "MISSING_BOUNDARY_MINUTE" if leg in missing else "AVAILABLE",
                "history": encode_history(history),
            }
        return result

    return cohort, calendar, captured, row
