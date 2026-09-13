from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sessionzero_bitget import CandleObservation, ReferenceDataBundle
from sqlalchemy import Engine, insert, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from .models import (
    CorporateActionRow,
    IngestionRun,
    NormalizedMarketCandle,
    RawMarketObservation,
    RawReferenceObservation,
    RealitySymbolMappingRow,
    ShareCapitalChangeRow,
    SourceSessionMetadataRow,
    SuspensionRecordRow,
)

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    run_id: uuid.UUID
    records_received: int
    raw_records_written: int
    normalized_records_written: int


@dataclass(frozen=True, slots=True)
class ReferenceIngestionResult:
    run_id: uuid.UUID
    records_received: int
    raw_records_written: int
    normalized_records_written: int


def _create_run(
    engine: Engine,
    *,
    provider: str,
    operation: str,
    started_at: datetime,
    requested_start: datetime | None,
    requested_end: datetime | None,
    interval: str | None,
    pages_requested: int | None,
    quality_status: str | None,
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
                requested_start=requested_start,
                requested_end=requested_end,
                interval=interval,
                pages_requested=pages_requested,
                quality_status=quality_status,
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
    records_received: int | None = None,
    requested_start: datetime | None = None,
    requested_end: datetime | None = None,
    interval: str | None = None,
    pages_requested: int | None = None,
    quality_status: str | None = None,
) -> IngestionResult:
    if not observations:
        raise ValueError("at least one candle observation is required")
    received = len(observations) if records_received is None else records_received
    if received < len(observations):
        raise ValueError("records_received cannot be smaller than unique observations")
    started_at = clock()
    run_id = _create_run(
        engine,
        provider=provider,
        operation=operation,
        started_at=started_at,
        requested_start=requested_start,
        requested_end=requested_end,
        interval=interval,
        pages_requested=pages_requested,
        quality_status=quality_status,
    )
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


def _provenance_values(record: object) -> dict[str, object]:
    return {
        "source": record.source,
        "provider_record_key": record.provider_record_key,
        "availability_time": record.availability_time,
        "availability_time_status": record.availability_time_status.value,
        "ingestion_time": record.ingestion_time,
        "endpoint": record.endpoint,
        "source_version": record.source_version,
        "raw_or_derived": record.raw_or_derived.value,
    }


def ingest_reference_bundle(
    engine: Engine,
    bundle: ReferenceDataBundle,
    *,
    provider: str = "bitget",
    operation: str = "reality_reference_data",
    clock: Clock = _utc_now,
) -> ReferenceIngestionResult:
    if not bundle.raw_responses:
        raise ValueError("reference bundle must retain raw responses")
    started_at = clock()
    run_id = _create_run(
        engine,
        provider=provider,
        operation=operation,
        started_at=started_at,
        requested_start=None,
        requested_end=None,
        interval=None,
        pages_requested=None,
        quality_status=None,
    )
    mapping = bundle.mapping
    mapping_values = {
        **_provenance_values(mapping),
        "reality_symbol": mapping.reality_symbol,
        "base_coin": mapping.base_coin,
        "native_ticker": mapping.native_ticker,
        "name": mapping.name,
        "trading_periods": list(mapping.trading_periods),
        "weekend_tradable": mapping.weekend_tradable,
        "effective_time": mapping.effective_time,
        "permanent_identifier": mapping.permanent_identifier,
    }
    action_values: list[dict[str, object]] = []
    for item in bundle.dividends:
        action_values.append(
            {
                "provider_symbol": None,
                "numerator": None,
                "denominator": None,
                "adjustment_ratio": None,
                "provider_status": None,
                "event_timezone": None,
                "trading_halt_start": None,
                "trading_halt_end": None,
                **_provenance_values(item),
                "native_ticker": item.native_ticker,
                "action_type": item.action_type.value,
                "announcement_date": item.announcement_date,
                "record_date": item.record_date,
                "ex_date": item.ex_date,
                "payment_date": item.payment_date,
                "effective_date": item.effective_date,
                "cash_amount_per_share": item.cash_amount_per_share,
                "stock_amount_per_share": item.stock_amount_per_share,
                "currency": item.currency,
            }
        )
    for item in bundle.splits:
        action_values.append(
            {
                "payment_date": None,
                "cash_amount_per_share": None,
                "stock_amount_per_share": None,
                "currency": None,
                **_provenance_values(item),
                "native_ticker": item.native_ticker,
                "provider_symbol": item.provider_symbol,
                "action_type": item.action_type.value,
                "announcement_date": item.announcement_date,
                "record_date": item.record_date,
                "ex_date": item.ex_date,
                "effective_date": item.effective_date,
                "numerator": item.numerator,
                "denominator": item.denominator,
                "adjustment_ratio": item.adjustment_ratio,
                "provider_status": item.provider_status,
                "event_timezone": item.event_timezone,
                "trading_halt_start": item.trading_halt_start,
                "trading_halt_end": item.trading_halt_end,
            }
        )
    share_values = [
        {
            **_provenance_values(item),
            "native_ticker": item.native_ticker,
            "announcement_date": item.announcement_date,
            "effective_date": item.effective_date,
            "total_shares": item.total_shares,
            "common_shares": item.common_shares,
            "preferred_shares": item.preferred_shares,
            "other_shares": item.other_shares,
            "special_explanation": item.special_explanation,
            "change_reason": item.change_reason,
        }
        for item in bundle.share_changes
    ]
    suspension_values = [
        {
            **_provenance_values(item),
            "native_ticker": item.native_ticker,
            "name": item.name,
            "suspension_date": item.suspension_date,
            "suspension_time": item.suspension_time.isoformat()
            if item.suspension_time is not None
            else None,
            "suspension_reason": item.suspension_reason,
            "suspension_price": item.suspension_price,
            "resumption_date": item.resumption_date,
            "resumption_quote_time": item.resumption_quote_time.isoformat()
            if item.resumption_quote_time is not None
            else None,
            "resumption_trading_time": item.resumption_trading_time.isoformat()
            if item.resumption_trading_time is not None
            else None,
            "event_timezone": item.event_timezone,
        }
        for item in bundle.suspensions
    ]
    session = bundle.source_session_metadata
    session_values = {
        **_provenance_values(session),
        "market": session.market,
        "daylight_type": session.daylight_type,
        "state_time_zone": session.state_time_zone,
        "calendar_time_zone": session.calendar_time_zone,
        "sessions": [item.model_dump(mode="json") for item in session.sessions],
        "closures": [item.model_dump(mode="json") for item in session.closures],
        "regular_closure_days": list(session.regular_closure_days),
    }
    try:
        with engine.begin() as connection:
            raw_result = connection.execute(
                postgresql_insert(RawReferenceObservation)
                .values(
                    [
                        {
                            "run_id": run_id,
                            "source": "bitget_uta_v3",
                            "endpoint": item.endpoint,
                            "request_params": item.params,
                            "payload": item.payload,
                            "provider_request_time": item.provider_request_time,
                            "ingestion_time": item.ingestion_time,
                            "provider_record_key": item.provider_record_key,
                            "source_version": "uta_v3",
                        }
                        for item in bundle.raw_responses
                    ]
                )
                .on_conflict_do_nothing(constraint="uq_raw_reference_response_per_run")
                .returning(RawReferenceObservation.id)
            )
            raw_written = len(raw_result.scalars().all())
            normalized_written = 0
            for model, constraint, values in (
                (RealitySymbolMappingRow, "uq_reality_mapping_version", [mapping_values]),
                (CorporateActionRow, "uq_corporate_action_version", action_values),
                (ShareCapitalChangeRow, "uq_share_capital_version", share_values),
                (SuspensionRecordRow, "uq_suspension_version", suspension_values),
                (SourceSessionMetadataRow, "uq_source_session_version", [session_values]),
            ):
                if not values:
                    continue
                result = connection.execute(
                    postgresql_insert(model)
                    .values(values)
                    .on_conflict_do_nothing(constraint=constraint)
                    .returning(model.id)
                )
                normalized_written += len(result.scalars().all())
            connection.execute(
                update(IngestionRun)
                .where(IngestionRun.run_id == run_id)
                .values(
                    finished_at=clock(),
                    status="SUCCEEDED",
                    records_received=bundle.normalized_record_count,
                    records_written=normalized_written,
                    error_code=None,
                )
            )
    except Exception:
        _finalize_failed(
            engine,
            run_id=run_id,
            finished_at=clock(),
            records_received=bundle.normalized_record_count,
            error_code="DATABASE_WRITE_FAILED",
        )
        raise
    return ReferenceIngestionResult(
        run_id=run_id,
        records_received=bundle.normalized_record_count,
        raw_records_written=raw_written,
        normalized_records_written=normalized_written,
    )
