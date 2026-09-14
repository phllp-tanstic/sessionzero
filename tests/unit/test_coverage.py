from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from sessionzero_bitget import (
    BitgetMarketClient,
    RequestTelemetry,
    build_coverage_member,
    build_coverage_profile,
    coverage_status_for,
    profile_reality_coverage,
)
from sessionzero_schemas import (
    CoverageStatus,
    QualityStatus,
    StructuralQualityStatus,
    UniverseMappingStatus,
    UniverseMember,
)

START = datetime(2026, 6, 1, tzinfo=UTC)
END = START + timedelta(days=90)
VERSION = "a" * 64


def _member(symbol: str = "RTESTUSDT") -> UniverseMember:
    return UniverseMember(
        reality_symbol=symbol,
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


def test_coverage_member_captures_duration_and_deterministic_oos_feasibility() -> None:
    result = build_coverage_member(
        _member(),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=_quality(
            start=START + timedelta(days=30),
            end=END - timedelta(hours=1),
        ),
    )
    assert result.earliest_observed_event_time == START + timedelta(days=30)
    assert result.latest_observed_event_time == END - timedelta(hours=1)
    assert result.observed_duration_days == 60
    assert result.observed_record_count == 1440
    assert result.minimum_total_history_days == 60
    assert result.minimum_oos_days == 30
    assert result.meets_duration_requirement is True
    assert result.final_oos_window_start == END - timedelta(days=30)
    assert result.pre_oos_observation_present is True
    assert result.oos_observation_present is True
    assert result.final_oos_feasible is True
    assert result.structural_quality_status == StructuralQualityStatus.PASS
    assert result.coverage_status == CoverageStatus.SUFFICIENT_MINIMUM_HISTORY


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"observed_record_count": 0}, CoverageStatus.HISTORY_UNAVAILABLE),
        ({"observed_duration_days": 59.999}, CoverageStatus.INSUFFICIENT_HISTORY),
        (
            {"structural_quality_status": StructuralQualityStatus.FAIL},
            CoverageStatus.DATA_QUALITY_FAILURE,
        ),
        ({"final_oos_feasible": False}, CoverageStatus.INSUFFICIENT_HISTORY),
    ],
)
def test_structural_and_chronological_coverage_classifications(
    kwargs: dict[str, object], expected: CoverageStatus
) -> None:
    values = {
        "observed_record_count": 1440,
        "observed_duration_days": 60.0,
        "quality_status": QualityStatus.PASS,
        "structural_quality_status": StructuralQualityStatus.PASS,
        "final_oos_feasible": True,
    }
    values.update(kwargs)
    assert coverage_status_for(**values) == expected  # type: ignore[arg-type]


def test_duration_requirement_fails_below_sixty_days() -> None:
    result = build_coverage_member(
        _member(),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=_quality(
            start=START + timedelta(days=31),
            end=END - timedelta(hours=1),
        ),
    )
    assert result.observed_duration_days == 59
    assert result.meets_duration_requirement is False
    assert result.final_oos_feasible is True
    assert result.coverage_status == CoverageStatus.INSUFFICIENT_HISTORY


def test_sixty_day_span_without_final_oos_observation_is_not_sufficient() -> None:
    result = build_coverage_member(
        _member(),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=_quality(),
    )
    assert result.meets_duration_requirement is True
    assert result.oos_observation_present is False
    assert result.final_oos_feasible is False
    assert result.coverage_status == CoverageStatus.INSUFFICIENT_HISTORY


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


def test_profiler_keeps_the_same_first_ten_and_window_without_synthetic_data() -> None:
    pilot_start = datetime(2026, 6, 15, 20, tzinfo=UTC)
    pilot_end = datetime(2026, 9, 13, 20, tzinfo=UTC)
    members = tuple(_member(f"R{index:02d}USDT") for index in range(11))

    def empty_history(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": "00000", "msg": "success", "requestTime": 1, "data": []},
        )

    with BitgetMarketClient(
        transport=httpx.MockTransport(empty_history), max_retries=0, clock=lambda: pilot_end
    ) as client:
        profile = profile_reality_coverage(
            client,
            universe_version=VERSION,
            interval="1H",
            universe_members=members,
            evaluation_start=pilot_start,
            evaluation_end=pilot_end,
            subset_size=10,
            clock=lambda: pilot_end,
        )
    assert [member.symbol for member in profile.members] == [
        f"R{index:02d}USDT" for index in range(10)
    ]
    assert profile.evaluation_start == pilot_start
    assert profile.evaluation_end == pilot_end
    assert all(member.observed_record_count == 0 for member in profile.members)
