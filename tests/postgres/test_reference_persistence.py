from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from sessionzero_bitget import RawReferenceResponse, ReferenceDataBundle
from sessionzero_database import (
    CorporateActionRow,
    RawReferenceObservation,
    RealitySymbolMappingRow,
    ingest_reference_bundle,
)
from sessionzero_schemas import (
    DividendRecord,
    MarketSessionWindow,
    RealitySymbolMapping,
    ReferenceActionType,
    SourceSessionMetadata,
)
from sqlalchemy import func, select

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 9, 13, 18, tzinfo=UTC)


def _bundle(*, amount: str = "0.25") -> ReferenceDataBundle:
    key = "a" * 64 if amount == "0.25" else "b" * 64
    mapping = RealitySymbolMapping(
        endpoint="/stock-info",
        provider_record_key="1" * 64,
        ingestion_time=NOW,
        reality_symbol="RAAPLUSDT",
        base_coin="rAAPL",
        native_ticker="AAPL",
        trading_periods=("regular",),
        weekend_tradable=False,
    )
    dividend = DividendRecord(
        endpoint="/dividends",
        provider_record_key=key,
        ingestion_time=NOW,
        native_ticker="AAPL",
        action_type=ReferenceActionType.CASH_DIVIDEND,
        ex_date=date(2026, 8, 1),
        effective_date=date(2026, 8, 1),
        cash_amount_per_share=Decimal(amount),
    )
    session = SourceSessionMetadata(
        endpoint="/states+/calendar",
        provider_record_key="2" * 64,
        ingestion_time=NOW,
        market="US",
        daylight_type="standard",
        state_time_zone="EST",
        calendar_time_zone="EST",
        sessions=(
            MarketSessionWindow(
                state="regular", time_zone="EST", start_time=time(9, 30), end_time=time(16)
            ),
        ),
        closures=(),
        regular_closure_days=("SATURDAY", "SUNDAY"),
    )
    raw = RawReferenceResponse(
        endpoint="/dividends",
        params={"code": "AAPL"},
        payload={"code": "00000", "data": [{"amount": amount}]},
        provider_request_time=NOW,
        ingestion_time=NOW,
        provider_record_key=key,
    )
    return ReferenceDataBundle(
        mapping=mapping,
        dividends=(dividend,),
        splits=(),
        share_changes=(),
        suspensions=(),
        source_session_metadata=session,
        raw_responses=(raw,),
    )


def test_reference_raw_retention_idempotency_and_correction(database_engine) -> None:
    first = ingest_reference_bundle(database_engine, _bundle())
    repeat = ingest_reference_bundle(database_engine, _bundle())
    corrected = ingest_reference_bundle(database_engine, _bundle(amount="0.30"))
    assert (
        first.normalized_records_written,
        repeat.normalized_records_written,
        corrected.normalized_records_written,
    ) == (3, 0, 1)
    assert (
        first.raw_records_written,
        repeat.raw_records_written,
        corrected.raw_records_written,
    ) == (1, 1, 1)
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(RawReferenceObservation)) == 3
        assert connection.scalar(select(func.count()).select_from(RealitySymbolMappingRow)) == 1
        assert connection.scalar(select(func.count()).select_from(CorporateActionRow)) == 2
