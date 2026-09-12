from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sessionzero_bitget import CandleObservation
from sqlalchemy import Engine, insert, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from .models import IngestionRun, NormalizedMarketCandle, RawMarketObservation

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    run_id: uuid.UUID
    records_received: int
    raw_records_written: int
    normalized_records_written: int


def _create_run(
    engine: Engine, *, provider: str, operation: str, started_at: datetime
) -> uuid.UUID:
    run_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(IngestionRun).values(
                run_id=run_id,
                provider=provider,
                operation=operation,
                started_at=started_at,
                status="RUNNING",
                records_received=0,
                records_written=0,
            )
        )
    return run_id


def _finalize_failed(
    engine: Engine,
    *,
    run_id: uuid.UUID,
    finished_at: datetime,
    records_received: int,
    error_code: str,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            update(IngestionRun)
            .where(IngestionRun.run_id == run_id)
            .values(
                finished_at=finished_at,
                status="FAILED",
                records_received=records_received,
                records_written=0,
                error_code=error_code,
            )
        )


def _raw_values(run_id: uuid.UUID, observation: CandleObservation) -> dict[str, object]:
    candle = observation.candle
    return {
        "run_id": run_id,
        "source": candle.source,
        "symbol": candle.symbol,
        "market": candle.market,
        "event_time": candle.event_time,
        "ingestion_time": candle.ingestion_time,
        "payload": {"row": observation.payload},
        "endpoint": observation.endpoint,
        "source_version": "uta_v3",
    }


def _normalized_values(observation: CandleObservation) -> dict[str, object]:
    candle = observation.candle
    return {
        "source": candle.source,
        "symbol": candle.symbol,
        "market": candle.market,
        "interval": candle.interval,
        "event_time": candle.event_time,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "turnover": candle.turnover,
        "ingestion_time": candle.ingestion_time,
    }


def ingest_candle_observations(
    engine: Engine,
    observations: Sequence[CandleObservation],
    *,
    provider: str = "bitget",
    operation: str = "history_candles",
    clock: Clock = _utc_now,
) -> IngestionResult:
    if not observations:
        raise ValueError("at least one candle observation is required")
    started_at = clock()
    run_id = _create_run(engine, provider=provider, operation=operation, started_at=started_at)
    received = len(observations)
    try:
        with engine.begin() as connection:
            raw_result = connection.execute(
                postgresql_insert(RawMarketObservation)
                .values([_raw_values(run_id, item) for item in observations])
                .on_conflict_do_nothing(constraint="uq_raw_observation_per_run")
                .returning(RawMarketObservation.id)
            )
            raw_written = len(raw_result.scalars().all())
            normalized_result = connection.execute(
                postgresql_insert(NormalizedMarketCandle)
                .values([_normalized_values(item) for item in observations])
                .on_conflict_do_nothing(constraint="uq_normalized_candle_market_identity")
                .returning(NormalizedMarketCandle.id)
            )
            normalized_written = len(normalized_result.scalars().all())
            connection.execute(
                update(IngestionRun)
                .where(IngestionRun.run_id == run_id)
                .values(
                    finished_at=clock(),
                    status="SUCCEEDED",
                    records_received=received,
                    records_written=normalized_written,
                    error_code=None,
                )
            )
    except Exception:
        _finalize_failed(
            engine,
            run_id=run_id,
            finished_at=clock(),
            records_received=received,
            error_code="DATABASE_WRITE_FAILED",
        )
        raise
    return IngestionResult(
        run_id=run_id,
        records_received=received,
        raw_records_written=raw_written,
        normalized_records_written=normalized_written,
    )
