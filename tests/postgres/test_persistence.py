from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sessionzero_bitget import CandleObservation
from sessionzero_database import (
    IngestionRun,
    NormalizedMarketCandle,
    RawMarketObservation,
    ingest_candle_observations,
)
from sessionzero_schemas import MarketCandle
from sqlalchemy import Engine, func, insert, select
from sqlalchemy.exc import IntegrityError

EVENT_TIME = datetime(2026, 6, 10, 0, 0, tzinfo=UTC)
INGESTION_TIME = datetime(2026, 9, 12, 14, 0, tzinfo=UTC)


def observation(
    *,
    close: str = "10.123456789012345678901234567890",
    high: str = "11.000000000000000000000000000001",
    low: str = "9.000000000000000000000000000001",
    volume: str | None = None,
    turnover: str | None = None,
    ingestion_time: datetime = INGESTION_TIME,
) -> CandleObservation:
    raw = [
        str(int(EVENT_TIME.timestamp() * 1000)),
        "10.000000000000000000000000000001",
        high,
        low,
        close,
        volume or "",
        turnover or "",
    ]
    return CandleObservation(
        payload=raw,
        endpoint="/api/v3/market/history-candles",
        candle=MarketCandle(
            source="bitget_uta_v3",
            symbol="RTESTUSDT",
            market="SPOT",
            interval="1H",
            event_time=EVENT_TIME,
            ingestion_time=ingestion_time,
            open=Decimal(raw[1]),
            high=Decimal(raw[2]),
            low=Decimal(raw[3]),
            close=Decimal(raw[4]),
            volume=Decimal(volume) if volume is not None else None,
            turnover=Decimal(turnover) if turnover is not None else None,
        ),
    )


@pytest.mark.postgres
def test_ingestion_run_raw_candle_utc_decimal_null_and_idempotency(
    database_engine: Engine,
) -> None:
    first = ingest_candle_observations(database_engine, [observation()])
    later = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    second = ingest_candle_observations(
        database_engine,
        [observation(ingestion_time=later)],
    )

    assert first.raw_records_written == 1
    assert first.normalized_records_written == 1
    assert second.raw_records_written == 1
    assert second.normalized_records_written == 0
    with database_engine.connect() as connection:
        runs = connection.execute(select(IngestionRun).order_by(IngestionRun.started_at)).all()
        raw_rows = connection.execute(select(RawMarketObservation)).all()
        candle = connection.execute(select(NormalizedMarketCandle)).one()
    assert len(runs) == 2
    assert [row.status for row in runs] == ["SUCCEEDED", "SUCCEEDED"]
    assert [row.records_written for row in runs] == [1, 0]
    assert len(raw_rows) == 2
    assert raw_rows[0].payload["row"][4] == "10.123456789012345678901234567890"
    assert candle.event_time.utcoffset().total_seconds() == 0
    assert candle.ingestion_time == INGESTION_TIME
    assert candle.close == Decimal("10.123456789012345678901234567890")
    assert candle.volume is None
    assert candle.turnover is None


@pytest.mark.postgres
def test_revision_is_audited_but_does_not_overwrite_normalized_row(
    database_engine: Engine,
) -> None:
    ingest_candle_observations(database_engine, [observation(close="10.1")])
    revised = ingest_candle_observations(database_engine, [observation(close="10.2")])
    with database_engine.connect() as connection:
        close = connection.scalar(select(NormalizedMarketCandle.close))
        payloads = connection.scalars(
            select(RawMarketObservation.payload).order_by(RawMarketObservation.id)
        ).all()
    assert revised.normalized_records_written == 0
    assert close == Decimal("10.100000000000000000")
    assert [item["row"][4] for item in payloads] == ["10.1", "10.2"]


@pytest.mark.postgres
def test_database_constraint_rejects_duplicate_normalized_identity(
    database_engine: Engine,
) -> None:
    ingest_candle_observations(database_engine, [observation()])
    values = {
        column.name: getattr(observation().candle, column.name)
        for column in NormalizedMarketCandle.__table__.columns
        if column.name not in {"id", "created_at"}
    }
    with pytest.raises(IntegrityError), database_engine.begin() as connection:
        connection.execute(insert(NormalizedMarketCandle).values(**values))


@pytest.mark.postgres
def test_raw_and_normalized_transaction_rolls_back_before_failed_status(
    database_engine: Engine,
) -> None:
    invalid = observation(high="8", low="9")
    with pytest.raises(IntegrityError):
        ingest_candle_observations(database_engine, [invalid])
    with database_engine.connect() as connection:
        run = connection.execute(select(IngestionRun)).one()
        raw_count = connection.scalar(select(func.count()).select_from(RawMarketObservation))
        candle_count = connection.scalar(select(func.count()).select_from(NormalizedMarketCandle))
    assert run.status == "FAILED"
    assert run.error_code == "DATABASE_WRITE_FAILED"
    assert run.records_received == 1
    assert run.records_written == 0
    assert raw_count == 0
    assert candle_count == 0


@pytest.mark.postgres
def test_nullable_and_non_null_quantities_round_trip(database_engine: Engine) -> None:
    ingest_candle_observations(
        database_engine,
        [
            observation(
                volume="0.000000000000000000000000000001",
                turnover="123.456789012345678901234567890123",
            )
        ],
    )
    with database_engine.connect() as connection:
        candle = connection.execute(select(NormalizedMarketCandle)).one()
    assert candle.volume == Decimal("0.000000000000000000000000000001")
    assert candle.turnover == Decimal("123.456789012345678901234567890123")
