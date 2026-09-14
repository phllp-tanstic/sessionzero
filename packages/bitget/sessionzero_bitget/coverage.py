from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sessionzero_market_data import CuratedBitgetSourceSessionProvider, SourceSessionProvider
from sessionzero_schemas import (
    CoverageEvaluationScope,
    CoverageStatus,
    HistoricalCoverageMember,
    HistoricalCoverageProfile,
    QualityStatus,
    UniverseMember,
)

from .client import BitgetMarketClient, RequestTelemetry
from .errors import BitgetProviderError
from .history import HistoryPaginationError, fetch_bounded_history
from .quality import INTERVAL_DURATIONS

COVERAGE_TRANSFORMATION_VERSION = "reality_historical_coverage.v3"
MINIMUM_TOTAL_HISTORY_DAYS = 60
MINIMUM_OOS_DAYS = 30
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _telemetry_delta(before: RequestTelemetry, after: RequestTelemetry) -> RequestTelemetry:
    return RequestTelemetry(
        request_count=after.request_count - before.request_count,
        retry_count=after.retry_count - before.retry_count,
        rate_limit_count=after.rate_limit_count - before.rate_limit_count,
    )


def coverage_status_for(
    *,
    observed_record_count: int,
    observed_duration_days: float,
    quality_status: QualityStatus | None,
    missing_while_expected_open: int,
    source_session_unknown_count: int,
    failure_code: str | None = None,
    minimum_total_history_days: int = MINIMUM_TOTAL_HISTORY_DAYS,
) -> CoverageStatus:
    if observed_record_count == 0:
        return CoverageStatus.HISTORY_UNAVAILABLE
    if quality_status == QualityStatus.FAIL:
        return CoverageStatus.DATA_QUALITY_FAILURE
    if failure_code is not None:
        return CoverageStatus.HISTORY_UNAVAILABLE
    if observed_duration_days < minimum_total_history_days:
        return CoverageStatus.INSUFFICIENT_HISTORY
    if source_session_unknown_count:
        return CoverageStatus.SOURCE_SESSION_TOO_UNKNOWN
    if missing_while_expected_open:
        return CoverageStatus.UNKNOWN
    return CoverageStatus.SUFFICIENT_MINIMUM_HISTORY


def build_coverage_member(
    member: UniverseMember,
    *,
    universe_version: str,
    interval: str,
    evaluation_start: datetime,
    evaluation_end: datetime,
    verification_time: datetime,
    quality: object | None,
    telemetry: RequestTelemetry | None = None,
    failure_code: str | None = None,
    source_session_evidence_ids: tuple[str, ...] = (),
) -> HistoricalCoverageMember:
    if member.native_ticker is None:
        raise ValueError("coverage profiling requires an explicit native ticker mapping")
    telemetry = telemetry or RequestTelemetry(0, 0, 0)
    observed_count = 0 if quality is None else quality.records_unique
    observed_start = None if quality is None else quality.observed_start
    observed_end = None if quality is None else quality.observed_end
    duration_days = 0.0
    if observed_start is not None and observed_end is not None:
        duration_days = (
            observed_end - observed_start + INTERVAL_DURATIONS[interval]
        ).total_seconds() / 86_400
    quality_status = None if quality is None else quality.quality_status
    missing = 0 if quality is None else quality.missing_count
    expected_open = (
        0
        if quality is None
        else getattr(quality, "expected_open_interval_count", quality.records_unique + missing)
    )
    observed_open = (
        0
        if quality is None
        else getattr(quality, "observed_while_expected_open_count", quality.records_unique)
    )
    expected_closed = (
        0 if quality is None else getattr(quality, "expected_closed_interval_count", 0)
    )
    observed_closed = (
        0 if quality is None else getattr(quality, "observed_while_expected_closed_count", 0)
    )
    unknown = (
        0
        if quality is None
        else getattr(
            quality, "source_session_unknown_interval_count", quality.source_session_unknown_count
        )
    )
    observed_unknown = (
        0
        if quality is None
        else getattr(quality, "observed_while_source_session_unknown_count", 0)
    )
    holiday_ambiguous = (
        0 if quality is None else getattr(quality, "holiday_ambiguous_interval_count", 0)
    )
    holiday_ambiguous_timestamps = (
        () if quality is None else getattr(quality, "holiday_ambiguous_timestamps", ())
    )
    total_intervals = expected_open + expected_closed + unknown
    observed_ratio = None if expected_open == 0 else Decimal(observed_open) / expected_open
    missing_ratio = None if expected_open == 0 else Decimal(missing) / expected_open
    unknown_fraction = Decimal(0) if total_intervals == 0 else Decimal(unknown) / total_intervals
    status = coverage_status_for(
        observed_record_count=observed_count,
        observed_duration_days=duration_days,
        quality_status=quality_status,
        missing_while_expected_open=missing,
        source_session_unknown_count=unknown,
        failure_code=failure_code,
    )
    return HistoricalCoverageMember(
        symbol=member.reality_symbol,
        native_ticker=member.native_ticker,
        interval=interval,
        transformation_version=COVERAGE_TRANSFORMATION_VERSION,
        evaluation_start=_as_utc(evaluation_start, "evaluation_start"),
        evaluation_end=_as_utc(evaluation_end, "evaluation_end"),
        earliest_observed_event_time=observed_start,
        latest_observed_event_time=observed_end,
        observed_duration_days=duration_days,
        observed_record_count=observed_count,
        expected_intervals_where_session_known=expected_open + expected_closed,
        missing_while_expected_open=missing,
        source_session_unknown_count=unknown,
        expected_open_interval_count=expected_open,
        observed_while_expected_open_count=observed_open,
        expected_closed_interval_count=expected_closed,
        observed_while_expected_closed_count=observed_closed,
        source_session_unknown_interval_count=unknown,
        observed_while_source_session_unknown_count=observed_unknown,
        holiday_ambiguous_interval_count=holiday_ambiguous,
        holiday_ambiguous_timestamps=holiday_ambiguous_timestamps,
        observed_over_known_expected=observed_ratio,
        missing_over_known_expected=missing_ratio,
        unknown_fraction=unknown_fraction,
        left_censored=observed_start == _as_utc(evaluation_start, "evaluation_start"),
        source_session_evidence_ids=source_session_evidence_ids,
        quality_status=None if quality_status is None else quality_status.value,
        coverage_status=status,
        request_count=telemetry.request_count,
        retry_count=telemetry.retry_count,
        rate_limit_count=telemetry.rate_limit_count,
        failure_code=failure_code,
        verification_time=_as_utc(verification_time, "verification_time"),
        universe_version=universe_version,
    )


def _profile_version(
    universe_version: str,
    interval: str,
    evaluation_start: datetime,
    evaluation_end: datetime,
    members: tuple[HistoricalCoverageMember, ...],
    lineage: dict[str, str | None],
) -> str:
    normalized_members = []
    for member in members:
        value = member.model_dump(mode="json")
        for operational_field in (
            "verification_time",
            "request_count",
            "retry_count",
            "rate_limit_count",
        ):
            value.pop(operational_field)
        normalized_members.append(value)
    return _hash(
        {
            "universe_version": universe_version,
            "interval": interval,
            "evaluation_start": _as_utc(evaluation_start, "evaluation_start").isoformat(),
            "evaluation_end": _as_utc(evaluation_end, "evaluation_end").isoformat(),
            "transformation_version": COVERAGE_TRANSFORMATION_VERSION,
            "lineage": lineage,
            "members": normalized_members,
        }
    )


def build_coverage_profile(
    *,
    universe_version: str,
    interval: str,
    evaluation_start: datetime,
    evaluation_end: datetime,
    generated_at: datetime,
    members: Sequence[HistoricalCoverageMember],
    evaluation_scope: CoverageEvaluationScope = CoverageEvaluationScope.CANONICAL_SUBSET,
    cohort_version: str | None = None,
    cohort_derivation_version: str | None = None,
    source_session_evidence_version: str | None = None,
    git_commit: str | None = None,
) -> HistoricalCoverageProfile:
    normalized = tuple(sorted(members, key=lambda item: item.symbol))
    lineage = {
        "evaluation_scope": evaluation_scope.value,
        "cohort_version": cohort_version,
        "cohort_derivation_version": cohort_derivation_version,
        "source_session_evidence_version": source_session_evidence_version,
        "git_commit": git_commit,
    }
    return HistoricalCoverageProfile(
        profile_version=_profile_version(
            universe_version, interval, evaluation_start, evaluation_end, normalized, lineage
        ),
        universe_version=universe_version,
        interval=interval,
        transformation_version=COVERAGE_TRANSFORMATION_VERSION,
        evaluation_start=_as_utc(evaluation_start, "evaluation_start"),
        evaluation_end=_as_utc(evaluation_end, "evaluation_end"),
        generated_at=_as_utc(generated_at, "generated_at"),
        evaluation_scope=evaluation_scope,
        cohort_version=cohort_version,
        cohort_derivation_version=cohort_derivation_version,
        source_session_evidence_version=source_session_evidence_version,
        git_commit=git_commit,
        members=normalized,
    )


def profile_reality_coverage(
    client: BitgetMarketClient,
    *,
    universe_version: str,
    interval: str,
    universe_members: Sequence[UniverseMember],
    evaluation_start: datetime,
    evaluation_end: datetime,
    subset_size: int = 10,
    page_limit: int = 100,
    max_pages: int = 100,
    allow_full_universe: bool = False,
    source_session_provider: SourceSessionProvider | None = None,
    clock: Clock = _utc_now,
    evaluation_scope: CoverageEvaluationScope = CoverageEvaluationScope.CANONICAL_SUBSET,
    cohort_version: str | None = None,
    cohort_derivation_version: str | None = None,
    source_session_evidence_version: str | None = None,
    git_commit: str | None = None,
    source_session_evidence_ids: dict[str, tuple[str, ...]] | None = None,
) -> HistoricalCoverageProfile:
    eligible = tuple(member for member in universe_members if member.technically_eligible)
    if subset_size < 1 or subset_size > len(eligible):
        raise ValueError("subset_size must select at least one available eligible member")
    if subset_size > 20 and not allow_full_universe:
        raise ValueError("more than 20 symbols requires explicit full-universe authorization")
    selected = eligible[:subset_size]
    sessions = source_session_provider or CuratedBitgetSourceSessionProvider()
    results: list[HistoricalCoverageMember] = []
    for member in selected:
        before = client.request_telemetry
        verification_time = _as_utc(clock(), "verification_time")
        quality = None
        failure_code = None
        try:
            history = fetch_bounded_history(
                client,
                symbol=member.reality_symbol,
                interval=interval,
                start=evaluation_start,
                end=evaluation_end,
                page_limit=page_limit,
                max_pages=max_pages,
                source_session_provider=sessions,
            )
            quality = history.quality
        except HistoryPaginationError as exc:
            quality = exc.report
            failure_code = exc.code
        except BitgetProviderError as exc:
            failure_code = exc.kind
        results.append(
            build_coverage_member(
                member,
                universe_version=universe_version,
                interval=interval,
                evaluation_start=evaluation_start,
                evaluation_end=evaluation_end,
                verification_time=verification_time,
                quality=quality,
                telemetry=_telemetry_delta(before, client.request_telemetry),
                failure_code=failure_code,
                source_session_evidence_ids=(source_session_evidence_ids or {}).get(
                    member.reality_symbol, ()
                ),
            )
        )
    return build_coverage_profile(
        universe_version=universe_version,
        interval=interval,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
        generated_at=clock(),
        members=results,
        evaluation_scope=evaluation_scope,
        cohort_version=cohort_version,
        cohort_derivation_version=cohort_derivation_version,
        source_session_evidence_version=source_session_evidence_version,
        git_commit=git_commit,
    )
