from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sessionzero_bitget import CandleObservation, HistoryPaginationError, fetch_bounded_history
from sessionzero_bitget.quality import evaluate_candle_quality
from sessionzero_market_data import (
    SourceAvailabilityState,
    SourceSessionAssessment,
    SourceSessionMode,
)
from sessionzero_schemas import MarketCandle, QualityStatus, StructuralQualityStatus

START = datetime(2026, 6, 10, tzinfo=UTC)
STEP = timedelta(hours=1)


def observation(
    hour: int,
    *,
    open_: str = "10",
    high: str = "11",
    low: str = "9",
    close: str = "10.5",
    volume: str | None = "1",
    turnover: str | None = "10.5",
) -> CandleObservation:
    event_time = START + hour * STEP
    row = [
        str(int(event_time.timestamp() * 1000)),
        open_,
        high,
        low,
        close,
        volume or "",
        turnover or "",
    ]
    return CandleObservation(
        payload=row,
        endpoint="/api/v3/market/history-candles",
        candle=MarketCandle(
            symbol="RTESTUSDT",
            market="SPOT",
            interval="1H",
            event_time=event_time,
            ingestion_time=datetime(2026, 9, 12, tzinfo=UTC),
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
            volume=Decimal(volume) if volume is not None else None,
            turnover=Decimal(turnover) if turnover is not None else None,
        ),
    )


class PageClient:
    def __init__(self, pages: list[list[CandleObservation]]) -> None:
        self.pages = pages
        self.calls: list[int | None] = []

    def get_candle_observation_page(
        self, _symbol: str, **kwargs: object
    ) -> list[CandleObservation]:
        self.calls.append(kwargs.get("end_time_ms"))  # type: ignore[arg-type]
        if not self.pages:
            raise AssertionError("unexpected extra page request")
        return self.pages.pop(0)


class StaticSourceSessionProvider:
    def __init__(self, state: SourceAvailabilityState) -> None:
        self.state = state

    def session_at(self, symbol: str, timestamp: datetime) -> SourceSessionAssessment:
        return SourceSessionAssessment(
            symbol=symbol,
            as_of=timestamp,
            availability=self.state,
            session_mode=SourceSessionMode.TWENTY_FOUR_SEVEN,
            reason="deterministic test provider",
        )


def quality(
    items: list[CandleObservation],
    *,
    end_hour: int = 3,
    state: SourceAvailabilityState = SourceAvailabilityState.EXPECTED_OPEN,
):
    return evaluate_candle_quality(
        items,
        symbol="RTESTUSDT",
        interval="1H",
        requested_start=START,
        requested_end=START + end_hour * STEP,
        page_count=1,
        source_session_provider=StaticSourceSessionProvider(state),
    )


def test_multiple_pages_are_bounded_sorted_and_complete() -> None:
    client = PageClient(
        [[observation(3), observation(4)], [observation(1), observation(2)], [observation(0)]]
    )
    result = fetch_bounded_history(  # type: ignore[arg-type]
        client,
        symbol="RTESTUSDT",
        interval="1H",
        start=START,
        end=START + 5 * STEP,
        page_limit=2,
        max_pages=3,
    )
    assert [item.candle.event_time for item in result.observations] == [
        START + hour * STEP for hour in range(5)
    ]
    assert result.quality.page_count == 3
    assert result.quality.records_received == 5
    assert result.quality.quality_status == QualityStatus.PASS
    assert len(client.calls) == 3


def test_overlapping_pages_are_deduplicated_and_reported() -> None:
    client = PageClient(
        [
            [observation(3), observation(4)],
            [observation(2), observation(3)],
            [observation(0), observation(1)],
        ]
    )
    result = fetch_bounded_history(  # type: ignore[arg-type]
        client,
        symbol="RTESTUSDT",
        interval="1H",
        start=START,
        end=START + 5 * STEP,
        page_limit=2,
        max_pages=3,
    )
    assert len(result.observations) == 5
    assert result.quality.records_received == 6
    assert result.quality.records_unique == 5
    assert result.quality.duplicate_count == 1
    assert result.quality.quality_status == QualityStatus.WARN


def test_pagination_no_progress_fails_without_looping() -> None:
    client = PageClient([[observation(5)]])
    with pytest.raises(HistoryPaginationError) as caught:
        fetch_bounded_history(  # type: ignore[arg-type]
            client,
            symbol="RTESTUSDT",
            interval="1H",
            start=START,
            end=START + 5 * STEP,
            page_limit=1,
        )
    assert caught.value.code == "PAGINATION_NO_PROGRESS"
    assert caught.value.report.pagination_error_count == 1
    assert caught.value.report.stale_pagination_count == 1
    assert len(client.calls) == 1


def test_maximum_page_guard_fails_before_an_extra_request() -> None:
    client = PageClient([[observation(3), observation(4)]])
    with pytest.raises(HistoryPaginationError) as caught:
        fetch_bounded_history(  # type: ignore[arg-type]
            client,
            symbol="RTESTUSDT",
            interval="1H",
            start=START,
            end=START + 5 * STEP,
            page_limit=2,
            max_pages=1,
        )
    assert caught.value.code == "MAX_PAGES_EXCEEDED"
    assert caught.value.report.pagination_error_count == 1
    assert caught.value.report.stale_pagination_count == 0
    assert len(client.calls) == 1


def test_half_open_clipping_excludes_outside_candles() -> None:
    client = PageClient([[observation(-1), observation(0), observation(1), observation(2)]])
    result = fetch_bounded_history(  # type: ignore[arg-type]
        client,
        symbol="RTESTUSDT",
        interval="1H",
        start=START,
        end=START + 2 * STEP,
        page_limit=100,
    )
    assert [item.candle.event_time for item in result.observations] == [START, START + STEP]
    assert result.quality.outside_range_count == 2
    assert result.quality.provider_boundary_spillover_count == 1
    assert result.quality.out_of_range_leakage_count == 1
    assert result.quality.quality_status == QualityStatus.FAIL
    assert result.quality.structural_quality_status == StructuralQualityStatus.FAIL


def test_verified_pre_start_spillover_is_clipped_without_structural_failure() -> None:
    accepted, report = quality([observation(-2), observation(-1), observation(0), observation(1)])
    assert [item.candle.event_time for item in accepted] == [START, START + STEP]
    assert report.provider_boundary_spillover_count == 2
    assert report.out_of_range_leakage_count == 0
    assert report.quality_status == QualityStatus.WARN
    assert report.structural_quality_status == StructuralQualityStatus.PASS


def test_post_end_timestamp_leakage_remains_structural_failure() -> None:
    accepted, report = quality([observation(0), observation(1), observation(3)])
    assert [item.candle.event_time for item in accepted] == [START, START + STEP]
    assert report.provider_boundary_spillover_count == 0
    assert report.out_of_range_leakage_count == 1
    assert report.structural_quality_status == StructuralQualityStatus.FAIL


def test_empty_result_has_machine_readable_failure() -> None:
    result = fetch_bounded_history(  # type: ignore[arg-type]
        PageClient([[]]),
        symbol="RTESTUSDT",
        interval="1H",
        start=START,
        end=START + 2 * STEP,
    )
    assert result.observations == ()
    assert result.quality.empty_result is True
    assert result.quality.quality_status == QualityStatus.FAIL
    assert {issue.code for issue in result.quality.issues} >= {
        "EMPTY_RESULT",
        "SOURCE_SESSION_UNKNOWN",
    }


def test_missing_interval_warns_without_creating_or_filling_a_candle() -> None:
    accepted, report = quality([observation(0, close="10"), observation(2, close="10.8")])
    assert len(accepted) == 2
    assert [item.candle.close for item in accepted] == [Decimal("10"), Decimal("10.8")]
    assert report.expected_candles == 3
    assert report.missing_count == 1
    assert report.missing_examples == (START + STEP,)
    assert report.quality_status == QualityStatus.WARN
    assert report.structural_quality_status == StructuralQualityStatus.PASS


def test_duplicate_and_out_of_order_timestamps_fail() -> None:
    accepted, report = quality([observation(0), observation(2), observation(1), observation(1)])
    assert len(accepted) == 3
    assert report.duplicate_count == 1
    assert report.out_of_order_count == 1
    assert report.quality_status == QualityStatus.FAIL


def test_impossible_ohlc_and_invalid_numeric_signs_fail() -> None:
    _, report = quality(
        [
            observation(0, open_="10", high="9", low="8", close="10"),
            observation(1, open_="0", high="1", low="0", close="0"),
            observation(2, volume="-1", turnover="-2"),
        ]
    )
    assert report.invalid_ohlc_count == 1
    assert report.non_positive_price_count == 1
    assert report.negative_volume_count == 1
    assert report.negative_turnover_count == 1
    assert report.quality_status == QualityStatus.FAIL


def test_nullable_volume_and_turnover_are_valid() -> None:
    _, report = quality(
        [
            observation(0, volume=None, turnover=None),
            observation(1, volume=None, turnover=None),
            observation(2, volume=None, turnover=None),
        ]
    )
    assert report.negative_volume_count == 0
    assert report.negative_turnover_count == 0
    assert report.quality_status == QualityStatus.PASS


def test_missing_examples_are_bounded_and_never_synthesized() -> None:
    accepted, report = quality([observation(0)], end_hour=30)
    assert len(accepted) == 1
    assert report.missing_count == 29
    assert len(report.missing_examples) == 10


def test_expected_source_closure_is_not_a_missing_data_defect() -> None:
    accepted, report = quality(
        [observation(0), observation(2)],
        state=SourceAvailabilityState.EXPECTED_CLOSED,
    )
    assert len(accepted) == 2
    assert report.missing_count == 0
    assert report.expected_source_closure_count == 1
    assert report.source_session_unknown_count == 0
    assert report.unexpected_spacing_count == 0
    assert report.quality_status == QualityStatus.PASS


def test_unknown_source_session_remains_explicit_without_synthetic_candle() -> None:
    accepted, report = quality(
        [observation(0), observation(2)],
        state=SourceAvailabilityState.UNKNOWN,
    )
    assert len(accepted) == 2
    assert report.missing_count == 0
    assert report.expected_source_closure_count == 0
    assert report.source_session_unknown_count == 1
    assert report.quality_status == QualityStatus.WARN
    assert "SOURCE_SESSION_UNKNOWN" in {issue.code for issue in report.issues}
