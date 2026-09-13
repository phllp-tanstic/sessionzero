from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sessionzero_bitget import (
    RequestTelemetry,
    build_coverage_member,
    build_coverage_profile,
    coverage_status_for,
)
from sessionzero_schemas import (
    CoverageStatus,
    QualityStatus,
    UniverseMappingStatus,
    UniverseMember,
)

START = datetime(2026, 6, 1, tzinfo=UTC)
END = START + timedelta(days=90)
VERSION = "a" * 64


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
        raw_metadata_key="b" * 64,
    )


def _quality(
    *,
    start: datetime = START,
    end: datetime = START + timedelta(days=60) - timedelta(hours=1),
    count: int = 1440,
    status: QualityStatus = QualityStatus.PASS,
    missing: int = 0,
    unknown: int = 0,
) -> object:
    return SimpleNamespace(
        records_unique=count,
        observed_start=start,
        observed_end=end,
        quality_status=status,
        missing_count=missing,
        source_session_unknown_count=unknown,
        expected_source_closure_count=0,
    )


def test_coverage_member_captures_bounds_duration_and_locked_requirements() -> None:
    result = build_coverage_member(
        _member(),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=_quality(),
    )
    assert result.earliest_observed_event_time == START
    assert result.latest_observed_event_time == START + timedelta(days=60) - timedelta(hours=1)
    assert result.observed_duration_days == 60
    assert result.observed_record_count == 1440
    assert result.minimum_total_history_days == 60
    assert result.minimum_oos_days == 30
    assert result.coverage_status == CoverageStatus.SUFFICIENT_MINIMUM_HISTORY


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"observed_record_count": 0}, CoverageStatus.HISTORY_UNAVAILABLE),
        ({"observed_duration_days": 59.999}, CoverageStatus.INSUFFICIENT_HISTORY),
        ({"quality_status": QualityStatus.FAIL}, CoverageStatus.DATA_QUALITY_FAILURE),
        ({"source_session_unknown_count": 1}, CoverageStatus.SOURCE_SESSION_TOO_UNKNOWN),
        ({"missing_while_expected_open": 1}, CoverageStatus.UNKNOWN),
    ],
)
def test_conservative_coverage_classifications(
    kwargs: dict[str, object], expected: CoverageStatus
) -> None:
    values = {
        "observed_record_count": 1440,
        "observed_duration_days": 60.0,
        "quality_status": QualityStatus.PASS,
        "missing_while_expected_open": 0,
        "source_session_unknown_count": 0,
    }
    values.update(kwargs)
    assert coverage_status_for(**values) == expected  # type: ignore[arg-type]


def test_profile_identity_excludes_wall_clock_and_retry_noise() -> None:
    first_member = build_coverage_member(
        _member(),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=_quality(),
        telemetry=RequestTelemetry(15, 0, 0),
    )
    repeat_member = first_member.model_copy(
        update={
            "verification_time": END + timedelta(hours=1),
            "request_count": 16,
            "retry_count": 1,
        }
    )
    first = build_coverage_profile(
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        generated_at=END,
        members=[first_member],
    )
    repeat = build_coverage_profile(
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        generated_at=END + timedelta(hours=1),
        members=[repeat_member],
    )
    assert first.profile_version == repeat.profile_version
    assert first.members[0].universe_version == VERSION


def test_coverage_times_must_be_utc() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_coverage_member(
            _member(),
            universe_version=VERSION,
            interval="1H",
            evaluation_start=START.replace(tzinfo=None),
            evaluation_end=END,
            verification_time=END,
            quality=None,
        )
