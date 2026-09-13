from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sessionzero_bitget import build_coverage_member, build_coverage_profile
from sessionzero_database import (
    HistoricalCoverageMemberRow,
    HistoricalCoverageProfileRow,
    load_accepted_universe,
    persist_historical_coverage_profile,
    persist_universe_snapshot,
)
from sessionzero_schemas import (
    QualityStatus,
    RealityUniverseSnapshot,
    UniverseMappingStatus,
    UniverseMember,
)
from sqlalchemy import func, select

pytestmark = pytest.mark.postgres
START = datetime(2026, 6, 1, tzinfo=UTC)
END = START + timedelta(days=90)
VERSION = "c" * 64


def _member() -> UniverseMember:
    return UniverseMember(
        reality_symbol="RTESTUSDT",
        base_coin="rTEST",
        quote_coin="USDT",
        native_ticker="TEST",
        instrument_status="online",
        is_reality=True,
        mapping_status=UniverseMappingStatus.AVAILABLE,
        source_session_status="UNKNOWN",
        source_session_mode="UNKNOWN",
        technically_eligible=True,
        exclusion_reasons=(),
        raw_metadata_key="d" * 64,
    )


def _profile():
    quality = type(
        "Quality",
        (),
        {
            "records_unique": 1440,
            "observed_start": START,
            "observed_end": START + timedelta(days=60) - timedelta(hours=1),
            "quality_status": QualityStatus.PASS,
            "missing_count": 0,
            "source_session_unknown_count": 0,
            "expected_source_closure_count": 0,
        },
    )()
    coverage_member = build_coverage_member(
        _member(),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=quality,
    )
    return build_coverage_profile(
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        generated_at=END,
        members=[coverage_member],
    )


def test_coverage_profile_is_linked_and_idempotent(database_engine) -> None:
    snapshot = RealityUniverseSnapshot(
        universe_version=VERSION,
        schema_version="reality_universe.v1",
        transformation_version="bitget_reality_universe.v1",
        generated_at=END,
        source="bitget_uta_v3",
        source_endpoint="/instruments+/stock-info",
        source_version="uta_v3",
        interval="1H",
        members=(_member(),),
        raw_provider_payload={"code": "00000", "data": []},
    )
    persist_universe_snapshot(database_engine, snapshot)
    loaded = load_accepted_universe(database_engine, VERSION)
    assert loaded.members == snapshot.members

    profile = _profile()
    assert persist_historical_coverage_profile(database_engine, profile)
    assert not persist_historical_coverage_profile(database_engine, profile)
    with database_engine.connect() as connection:
        assert (
            connection.scalar(select(func.count()).select_from(HistoricalCoverageProfileRow)) == 1
        )
        assert connection.scalar(select(func.count()).select_from(HistoricalCoverageMemberRow)) == 1
