"""Append-only native history persistence; no implicit latest-version selection."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sessionzero_market_data.native import NativeDataError, NativeHistory
from sqlalchemy import Engine, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import IngestionRun, NormalizedNativeEquityCandle, RawNativeEquityObservation

TRANSFORMATION = "native_equity_minute.v1"


def _canonical(value: object) -> str:
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value)


def persist_native_history(engine: Engine, history: NativeHistory) -> dict:
    if not history.pages or history.start >= history.end:
        raise NativeDataError("INVALID_HISTORY")
    previous = None
    for candle in history.candles:
        if not history.start <= candle.event_time < history.end:
            raise NativeDataError("PERSISTENCE_BOUNDARY_LEAKAGE")
        if previous is not None and candle.event_time <= previous:
            raise NativeDataError("PERSISTENCE_DUPLICATE_OR_ORDER")
        if (
            candle.source != history.source
            or candle.native_ticker != history.instrument.native_ticker
            or candle.page_index >= len(history.pages)
        ):
            raise NativeDataError("PERSISTENCE_LINEAGE_MISMATCH")
        previous = candle.event_time
    run_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(IngestionRun).values(
                run_id=run_id,
                provider=history.source,
                operation="native_equity_history",
                started_at=datetime.now(UTC),
                status="RUNNING",
                records_received=len(history.candles),
                records_written=0,
                requested_start=history.start,
                requested_end=history.end,
                interval="1Min",
                pages_requested=len(history.pages),
                quality_status="WARN" if history.clipped_count or not history.candles else "PASS",
            )
        )
    written = 0
    try:
        with engine.begin() as connection:
            page_ids = []
            for index, page in enumerate(history.pages):
                page_ids.append(
                    connection.scalar(
                        insert(RawNativeEquityObservation)
                        .values(
                            run_id=run_id,
                            page_index=index,
                            source=history.source,
                            native_ticker=history.instrument.native_ticker,
                            reality_symbol=history.instrument.reality_symbol,
                            universe_version=history.instrument.universe_version,
                            cohort_version=history.instrument.cohort_version,
                            endpoint=page.endpoint,
                            request_params=page.params,
                            response_headers=page.response_headers,
                            response_body=page.body,
                            requested_start=history.start,
                            requested_end=history.end,
                            ingestion_time=page.ingestion_time,
                        )
                        .returning(RawNativeEquityObservation.id)
                    )
                )
            for candle in history.candles:
                values = candle.model_dump(exclude={"page_index"})
                identity = {k: _canonical(v) for k, v in values.items() if k != "ingestion_time"}
                version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
                inserted = connection.scalar(
                    pg_insert(NormalizedNativeEquityCandle)
                    .values(
                        **values,
                        raw_observation_id=page_ids[candle.page_index],
                        content_version=version,
                        transformation_version=TRANSFORMATION,
                    )
                    .on_conflict_do_nothing(constraint="uq_native_candle_version")
                    .returning(NormalizedNativeEquityCandle.id)
                )
                written += inserted is not None
            connection.execute(
                update(IngestionRun)
                .where(IngestionRun.run_id == run_id)
                .values(
                    status="SUCCEEDED",
                    finished_at=datetime.now(UTC),
                    records_written=written,
                )
            )
    except Exception:
        with engine.begin() as connection:
            connection.execute(
                update(IngestionRun)
                .where(IngestionRun.run_id == run_id)
                .values(
                    status="FAILED",
                    finished_at=datetime.now(UTC),
                    error_code="NATIVE_DATABASE_WRITE",
                )
            )
        raise NativeDataError("NATIVE_DATABASE_WRITE") from None
    return {
        "run_id": str(run_id),
        "raw_pages_written": len(history.pages),
        "normalized_versions_written": written,
    }
