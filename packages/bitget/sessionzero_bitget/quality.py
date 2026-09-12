from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise

from sessionzero_market_data import SourceAvailabilityState, SourceSessionProvider
from sessionzero_schemas import (
    CandleQualityReport,
    QualityIssue,
    QualitySeverity,
    QualityStatus,
)

from .client import CandleObservation

INTERVAL_DURATIONS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1H": timedelta(hours=1),
    "4H": timedelta(hours=4),
    "1D": timedelta(days=1),
}
MAX_ISSUE_EXAMPLES = 10


def _identity(item: CandleObservation) -> tuple[str, str, str, str, datetime]:
    candle = item.candle
    return candle.source, candle.symbol, candle.market, candle.interval, candle.event_time


def _expected_times(start: datetime, end: datetime, step: timedelta) -> list[datetime]:
    step_microseconds = int(step.total_seconds() * 1_000_000)
    start_microseconds = int(start.timestamp() * 1_000_000)
    first = (start_microseconds + step_microseconds - 1) // step_microseconds * step_microseconds
    current = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=first)
    expected: list[datetime] = []
    while current < end:
        expected.append(current)
        current += step
    return expected


def _issue(
    code: str, severity: QualitySeverity, values: Sequence[datetime | str]
) -> QualityIssue | None:
    if not values:
        return None
    return QualityIssue(
        code=code,
        severity=severity,
        count=len(values),
        examples=tuple(
            value.isoformat() if isinstance(value, datetime) else value
            for value in values[:MAX_ISSUE_EXAMPLES]
        ),
    )


def evaluate_candle_quality(
    observations: Sequence[CandleObservation],
    *,
    symbol: str,
    interval: str,
    requested_start: datetime,
    requested_end: datetime,
    page_count: int,
    records_received: int | None = None,
    pagination_error_count: int = 0,
    stale_pagination_count: int = 0,
    pagination_error_code: str | None = None,
    overlap_duplicate_count: int = 0,
    overlap_duplicate_examples: Sequence[datetime] = (),
    source_session_provider: SourceSessionProvider | None = None,
) -> tuple[tuple[CandleObservation, ...], CandleQualityReport]:
    step = INTERVAL_DURATIONS[interval]
    identities = [_identity(item) for item in observations]
    identity_counts = Counter(identities)
    duplicate_times = [key[-1] for key, count in identity_counts.items() for _ in range(count - 1)]

    unique_by_identity: dict[tuple[str, str, str, str, datetime], CandleObservation] = {}
    for item in observations:
        unique_by_identity.setdefault(_identity(item), item)
    unique = list(unique_by_identity.values())

    out_of_order = [
        current.candle.event_time
        for previous, current in pairwise(observations)
        if current.candle.event_time < previous.candle.event_time
    ]
    outside = [
        item.candle.event_time
        for item in unique
        if not requested_start <= item.candle.event_time < requested_end
    ]
    accepted = sorted(
        (item for item in unique if requested_start <= item.candle.event_time < requested_end),
        key=lambda item: item.candle.event_time,
    )

    invalid_ohlc: list[datetime] = []
    non_positive: list[datetime] = []
    negative_volume: list[datetime] = []
    negative_turnover: list[datetime] = []
    for item in accepted:
        candle = item.candle
        prices = (candle.open, candle.high, candle.low, candle.close)
        if any(price <= Decimal(0) for price in prices):
            non_positive.append(candle.event_time)
        if not (
            candle.high >= candle.open
            and candle.high >= candle.close
            and candle.high >= candle.low
            and candle.low <= candle.open
            and candle.low <= candle.close
        ):
            invalid_ohlc.append(candle.event_time)
        if candle.volume is not None and candle.volume < 0:
            negative_volume.append(candle.event_time)
        if candle.turnover is not None and candle.turnover < 0:
            negative_turnover.append(candle.event_time)

    event_times = [item.candle.event_time for item in accepted]
    expected = _expected_times(requested_start, requested_end, step)
    absent = sorted(set(expected).difference(event_times))
    missing: list[datetime] = []
    expected_closures: list[datetime] = []
    unknown_sessions: list[datetime] = []
    for timestamp in absent:
        availability = (
            SourceAvailabilityState.UNKNOWN
            if source_session_provider is None
            else source_session_provider.session_at(symbol, timestamp).availability
        )
        if availability == SourceAvailabilityState.EXPECTED_OPEN:
            missing.append(timestamp)
        elif availability == SourceAvailabilityState.EXPECTED_CLOSED:
            expected_closures.append(timestamp)
        else:
            unknown_sessions.append(timestamp)
    unexpected_spacing = [
        current
        for previous, current in pairwise(event_times)
        if (index := bisect_right(missing, previous)) < len(missing) and missing[index] < current
    ]

    issues = [
        _issue("DUPLICATE_TIMESTAMP", QualitySeverity.ERROR, duplicate_times),
        _issue("OUT_OF_ORDER_TIMESTAMP", QualitySeverity.ERROR, out_of_order),
        _issue("TIMESTAMP_OUTSIDE_RANGE", QualitySeverity.ERROR, outside),
        _issue("INVALID_OHLC", QualitySeverity.ERROR, invalid_ohlc),
        _issue("NON_POSITIVE_PRICE", QualitySeverity.ERROR, non_positive),
        _issue("NEGATIVE_VOLUME", QualitySeverity.ERROR, negative_volume),
        _issue("NEGATIVE_TURNOVER", QualitySeverity.ERROR, negative_turnover),
        _issue("MISSING_WHILE_EXPECTED_OPEN", QualitySeverity.WARNING, missing),
        _issue("UNEXPECTED_INTERVAL_SPACING", QualitySeverity.WARNING, unexpected_spacing),
        _issue("EXPECTED_SOURCE_CLOSURE", QualitySeverity.INFO, expected_closures),
        _issue("SOURCE_SESSION_UNKNOWN", QualitySeverity.WARNING, unknown_sessions),
        _issue(
            "OVERLAPPING_PAGE_DUPLICATE",
            QualitySeverity.WARNING,
            overlap_duplicate_examples,
        ),
    ]
    if pagination_error_count:
        issues.append(
            QualityIssue(
                code=pagination_error_code or "STALE_PAGINATION",
                severity=QualitySeverity.ERROR,
                count=pagination_error_count,
            )
        )
    if not accepted:
        issues.append(QualityIssue(code="EMPTY_RESULT", severity=QualitySeverity.ERROR, count=1))
    filtered_issues = tuple(issue for issue in issues if issue is not None)
    if any(issue.severity == QualitySeverity.ERROR for issue in filtered_issues):
        status = QualityStatus.FAIL
    elif any(issue.severity == QualitySeverity.WARNING for issue in filtered_issues):
        status = QualityStatus.WARN
    else:
        status = QualityStatus.PASS

    report = CandleQualityReport(
        symbol=symbol,
        interval=interval,
        requested_start=requested_start,
        requested_end=requested_end,
        observed_start=event_times[0] if event_times else None,
        observed_end=event_times[-1] if event_times else None,
        page_count=page_count,
        records_received=len(observations) if records_received is None else records_received,
        records_unique=len(accepted),
        expected_candles=len(expected),
        missing_count=len(missing),
        missing_examples=tuple(missing[:MAX_ISSUE_EXAMPLES]),
        expected_source_closure_count=len(expected_closures),
        expected_source_closure_examples=tuple(expected_closures[:MAX_ISSUE_EXAMPLES]),
        source_session_unknown_count=len(unknown_sessions),
        source_session_unknown_examples=tuple(unknown_sessions[:MAX_ISSUE_EXAMPLES]),
        duplicate_count=len(duplicate_times) + overlap_duplicate_count,
        out_of_order_count=len(out_of_order),
        unexpected_spacing_count=len(unexpected_spacing),
        invalid_ohlc_count=len(invalid_ohlc),
        non_positive_price_count=len(non_positive),
        negative_volume_count=len(negative_volume),
        negative_turnover_count=len(negative_turnover),
        outside_range_count=len(outside),
        pagination_error_count=pagination_error_count,
        stale_pagination_count=stale_pagination_count,
        empty_result=not accepted,
        quality_status=status,
        issues=filtered_issues,
    )
    return tuple(accepted), report
