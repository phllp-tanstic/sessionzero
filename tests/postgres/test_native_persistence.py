from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sessionzero_database.models import (
    IngestionRun,
    NormalizedNativeEquityCandle,
    RawNativeEquityObservation,
)
from sessionzero_database.native import persist_native_history
from sessionzero_market_data.native import (
    NativeCandle,
    NativeDataError,
    NativeHistory,
    NativeInstrument,
    NativePage,
)
from sqlalchemy import func, select

pytestmark = pytest.mark.postgres


def history():
    event = datetime(2026, 6, 16, 13, 30, tzinfo=UTC)
    ingestion = datetime(2026, 9, 19, tzinfo=UTC)
    instrument = NativeInstrument(
        reality_symbol="TEST_MAPPING",
        native_ticker="AAPL",
        universe_version="a" * 64,
        cohort_version="b" * 64,
    )
    candle = NativeCandle(
        source="alpaca",
        native_ticker="AAPL",
        feed="sip",
        event_time=event,
        ingestion_time=ingestion,
        session_date=date(2026, 6, 16),
        open=Decimal("100.00000000000000000000000000001"),
        high=102,
        low=99,
        close=101,
        volume=10,
        trade_count=2,
        page_index=0,
    )
    page = NativePage(
        "https://data.alpaca.markets/v2/stocks/AAPL/bars",
        {"feed": "sip", "adjustment": "raw"},
        ingestion,
        {"x-request-id": "synthetic-test"},
        '{"test_only":true}',
    )
    return NativeHistory(
        instrument, event, event + timedelta(minutes=1), (page,), (candle,), "alpaca"
    )


def test_native_raw_retention_idempotency_and_corrections(database_engine):
    first = history()
    second = replace(
        first,
        candles=(
            first.candles[0].model_copy(
                update={"ingestion_time": first.candles[0].ingestion_time + timedelta(hours=1)}
            ),
        ),
    )
    corrected = replace(
        first, candles=(first.candles[0].model_copy(update={"close": Decimal("100.5")}),)
    )
    assert persist_native_history(database_engine, first)["normalized_versions_written"] == 1
    assert persist_native_history(database_engine, second)["normalized_versions_written"] == 0
    assert persist_native_history(database_engine, corrected)["normalized_versions_written"] == 1
    with database_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(RawNativeEquityObservation)) == 3
        rows = (
            conn.execute(
                select(NormalizedNativeEquityCandle.__table__).order_by(
                    NormalizedNativeEquityCandle.id
                )
            )
            .mappings()
            .all()
        )
        assert len(rows) == 2
        assert rows[0]["close"] == Decimal("101") and rows[1]["close"] == Decimal("100.5")
        assert rows[0]["open"] == first.candles[0].open
        assert rows[0]["event_time"].utcoffset() == timedelta(0)
        assert rows[0]["ingestion_time"] == first.candles[0].ingestion_time
        assert conn.scalar(select(RawNativeEquityObservation.response_body).limit(1)) == (
            '{"test_only":true}'
        )


def test_native_empty_history_retains_raw_and_no_synthetic_rows(database_engine):
    assert (
        persist_native_history(database_engine, replace(history(), candles=()))[
            "normalized_versions_written"
        ]
        == 0
    )
    with database_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(RawNativeEquityObservation)) == 1
        assert conn.scalar(select(func.count()).select_from(NormalizedNativeEquityCandle)) == 0


def test_native_boundary_guard(database_engine):
    source = history()
    bad = replace(source, start=source.end, end=source.end + timedelta(minutes=1))
    with pytest.raises(NativeDataError, match="BOUNDARY"):
        persist_native_history(database_engine, bad)
    with database_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(IngestionRun)) == 0


def test_native_transaction_rollback_keeps_failed_run(database_engine):
    source = history()
    # Fault injection bypasses Pydantic to exercise the independent database constraint.
    bad = replace(source, candles=(source.candles[0].model_copy(update={"low": Decimal(-1)}),))
    with pytest.raises(NativeDataError, match="DATABASE_WRITE"):
        persist_native_history(database_engine, bad)
    with database_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(RawNativeEquityObservation)) == 0
        assert conn.scalar(select(func.count()).select_from(NormalizedNativeEquityCandle)) == 0
        assert conn.scalar(select(IngestionRun.status)) == "FAILED"
