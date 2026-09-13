from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from sessionzero_bitget import BitgetMarketClient
from sessionzero_database import persist_historical_manifest, persist_universe_snapshot
from sessionzero_database.models import (
    HistoricalIngestionManifestEntryRow,
    HistoricalIngestionManifestRow,
    UniverseDiscoveryObservationRow,
    UniverseSnapshotMemberRow,
    UniverseSnapshotRow,
)
from sessionzero_database.universe import ingest_manifest_subset
from sessionzero_schemas import RealityUniverseSnapshot, UniverseMappingStatus, UniverseMember
from sqlalchemy import func, select

pytestmark = pytest.mark.postgres
START = datetime(2026, 9, 14, 14, tzinfo=UTC)
END = datetime(2026, 9, 14, 16, tzinfo=UTC)


def _member(symbol: str) -> UniverseMember:
    return UniverseMember(
        reality_symbol=symbol,
        base_coin=f"r{symbol}",
        quote_coin="USDT",
        native_ticker=symbol,
        instrument_status="online",
        is_reality=True,
        trading_periods=("regular",),
        weekend_tradable=False,
        mapping_status=UniverseMappingStatus.AVAILABLE,
        source_session_status="EXPECTED_OPEN",
        source_session_mode="24_5",
        technically_eligible=True,
        exclusion_reasons=(),
        raw_metadata_key=(symbol.lower()[0] * 64),
    )


def _snapshot() -> RealityUniverseSnapshot:
    return RealityUniverseSnapshot(
        universe_version="f" * 64,
        schema_version="reality_universe.v1",
        transformation_version="bitget_reality_universe.v1",
        generated_at=START,
        source="bitget_uta_v3",
        source_endpoint="/instruments+/stock-info",
        source_version="uta_v3",
        interval="1H",
        members=tuple(_member(symbol) for symbol in ("A", "B", "C")),
        raw_provider_payload={"code": "00000", "data": ["raw"]},
    )


def test_snapshot_idempotency_retains_each_raw_discovery(database_engine) -> None:
    first = persist_universe_snapshot(database_engine, _snapshot())
    repeat = persist_universe_snapshot(database_engine, _snapshot())
    assert (first.snapshot_written, first.members_written) == (True, 3)
    assert (repeat.snapshot_written, repeat.members_written) == (False, 0)
    with database_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(UniverseSnapshotRow)) == 1
        assert connection.scalar(select(func.count()).select_from(UniverseSnapshotMemberRow)) == 3
        assert (
            connection.scalar(select(func.count()).select_from(UniverseDiscoveryObservationRow))
            == 2
        )


def test_manifest_records_success_warning_and_isolated_failure(database_engine) -> None:
    persist_universe_snapshot(database_engine, _snapshot())

    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params["symbol"]
        if symbol == "C":
            return httpx.Response(
                200,
                json={
                    "code": "40001",
                    "msg": "unavailable",
                    "requestTime": 1789306347000,
                    "data": None,
                },
            )
        timestamps = [int(START.timestamp() * 1000), int((START.timestamp() + 3600) * 1000)]
        if symbol == "B":
            timestamps = timestamps[:1]
        rows = [[str(value), "10", "11", "9", "10", "1", "10"] for value in timestamps]
        return httpx.Response(
            200,
            json={"code": "00000", "msg": "success", "requestTime": 1789306347000, "data": rows},
        )

    with BitgetMarketClient(
        transport=httpx.MockTransport(handler), max_retries=0, clock=lambda: END
    ) as client:
        manifest = ingest_manifest_subset(
            database_engine,
            client,
            _snapshot(),
            start=START,
            end=END,
            subset_size=3,
            git_commit="abc123",
            clock=lambda: END,
        )
    assert [entry.status.value for entry in manifest.entries] == [
        "SUCCEEDED",
        "SUCCEEDED_WITH_WARNINGS",
        "UNAVAILABLE",
    ]
    assert manifest.entries[0].ingestion_run_id is not None
    assert manifest.entries[0].records_available_for_requested_window == 2
    assert manifest.entries[2].failure_code == "UPSTREAM_PROVIDER_ERROR"
    assert persist_historical_manifest(database_engine, manifest)
    assert not persist_historical_manifest(database_engine, manifest)
    with database_engine.connect() as connection:
        assert (
            connection.scalar(select(func.count()).select_from(HistoricalIngestionManifestRow)) == 1
        )
        assert (
            connection.scalar(select(func.count()).select_from(HistoricalIngestionManifestEntryRow))
            == 3
        )
