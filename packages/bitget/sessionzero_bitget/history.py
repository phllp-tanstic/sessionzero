from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sessionzero_market_data import SourceSessionProvider
from sessionzero_schemas import CandleQualityReport

from .client import REALITY_INTERVALS, BitgetMarketClient, CandleObservation
from .quality import evaluate_candle_quality

MAX_HISTORY_RANGE = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class BoundedHistoryResult:
    observations: tuple[CandleObservation, ...]
    quality: CandleQualityReport


class HistoryPaginationError(ValueError):
    def __init__(self, code: str, message: str, report: CandleQualityReport) -> None:
        super().__init__(message)
        self.code = code
        self.report = report

    def as_dict(self) -> dict[str, object]:
        return {
            "error": {"code": self.code, "message": str(self)},
            "quality": self.report.model_dump(mode="json"),
        }


def _require_bounded_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must be timezone-aware")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end must be timezone-aware")
    start = start.astimezone(UTC)
    end = end.astimezone(UTC)
    if start >= end:
        raise ValueError("start must be earlier than end")
    if end - start > MAX_HISTORY_RANGE:
        raise ValueError("bounded historical range cannot exceed 90 days")
    return start, end


def _pagination_failure(
    observations: Sequence[CandleObservation],
    *,
    code: str,
    message: str,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    page_count: int,
    records_received: int,
    source_session_provider: SourceSessionProvider | None,
) -> HistoryPaginationError:
    _, report = evaluate_candle_quality(
        observations,
        symbol=symbol,
        interval=interval,
        requested_start=start,
        requested_end=end,
        page_count=page_count,
        records_received=records_received,
        pagination_error_count=1,
        stale_pagination_count=int(code == "PAGINATION_NO_PROGRESS"),
        pagination_error_code=code,
        source_session_provider=source_session_provider,
    )
    return HistoryPaginationError(code, message, report)


def fetch_bounded_history(
    client: BitgetMarketClient,
    *,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    page_limit: int = 100,
    max_pages: int = 100,
    source_session_provider: SourceSessionProvider | None = None,
) -> BoundedHistoryResult:
    start, end = _require_bounded_range(start, end)
    if interval not in REALITY_INTERVALS:
        raise ValueError(f"unsupported Reality interval: {interval}")
    if not 1 <= page_limit <= 100:
        raise ValueError("historical page_limit must be between 1 and 100")
    if not 1 <= max_pages <= 10_000:
        raise ValueError("max_pages must be between 1 and 10000")

    pages_newest_first: list[list[CandleObservation]] = []
    cursor_end = end
    records_received = 0
    while True:
        if len(pages_newest_first) >= max_pages:
            flattened = [item for page in reversed(pages_newest_first) for item in page]
            raise _pagination_failure(
                flattened,
                code="MAX_PAGES_EXCEEDED",
                message="historical pagination reached the configured maximum page count",
                symbol=symbol,
                interval=interval,
                start=start,
                end=end,
                page_count=len(pages_newest_first),
                records_received=records_received,
                source_session_provider=source_session_provider,
            )
        page = client.get_candle_observation_page(
            symbol,
            interval=interval,
            limit=page_limit,
            historical=True,
            start_time_ms=int(start.timestamp() * 1000),
            end_time_ms=int(cursor_end.timestamp() * 1000),
        )
        pages_newest_first.append(page)
        records_received += len(page)
        if not page:
            break
        oldest = min(item.candle.event_time for item in page)
        if oldest >= cursor_end:
            flattened = [item for chunk in reversed(pages_newest_first) for item in chunk]
            raise _pagination_failure(
                flattened,
                code="PAGINATION_NO_PROGRESS",
                message="Bitget historical pagination did not move to an earlier timestamp",
                symbol=symbol,
                interval=interval,
                start=start,
                end=end,
                page_count=len(pages_newest_first),
                records_received=records_received,
                source_session_provider=source_session_provider,
            )
        if oldest <= start or len(page) < page_limit:
            break
        cursor_end = oldest

    provider_order: list[CandleObservation] = []
    seen_pages: dict[tuple[object, ...], tuple[int, CandleObservation]] = {}
    overlap_examples: list[datetime] = []
    for page_number, page in enumerate(reversed(pages_newest_first)):
        for item in page:
            candle = item.candle
            identity = (
                candle.source,
                candle.symbol,
                candle.market,
                candle.interval,
                candle.event_time,
            )
            prior = seen_pages.get(identity)
            if prior is not None and prior[0] != page_number and prior[1].payload == item.payload:
                overlap_examples.append(candle.event_time)
                continue
            seen_pages.setdefault(identity, (page_number, item))
            provider_order.append(item)
    observations, report = evaluate_candle_quality(
        provider_order,
        symbol=symbol,
        interval=interval,
        requested_start=start,
        requested_end=end,
        page_count=len(pages_newest_first),
        records_received=records_received,
        overlap_duplicate_count=len(overlap_examples),
        overlap_duplicate_examples=overlap_examples,
        source_session_provider=source_session_provider,
    )
    return BoundedHistoryResult(observations=observations, quality=report)
