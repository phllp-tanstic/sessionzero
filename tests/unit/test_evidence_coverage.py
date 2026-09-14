from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sessionzero_bitget import (
    EVIDENCE_COHORT_EVALUATION_END,
    EVIDENCE_COHORT_EVALUATION_START,
    build_coverage_member,
    derive_evidence_qualified_cohort,
)
from sessionzero_bitget.quality import evaluate_candle_quality
from sessionzero_market_data import (
    CuratedBitgetSourceSessionProvider,
    SourceSessionCapabilityKind,
    SourceSessionEvidence,
    SourceSessionEvidenceConfidence,
    SourceSessionEvidenceDataset,
    SourceSessionEvidenceType,
    SourceSessionMode,
)
from sessionzero_schemas import QualityStatus, UniverseMappingStatus, UniverseMember

VERSION = "a" * 64
START = EVIDENCE_COHORT_EVALUATION_START
END = EVIDENCE_COHORT_EVALUATION_END


def _member(symbol: str, native_ticker: str | None = "TEST") -> UniverseMember:
    return UniverseMember(
        reality_symbol=symbol,
        base_coin=symbol.removesuffix("USDT"),
        quote_coin="USDT",
        native_ticker=native_ticker,
        instrument_status="online",
        is_reality=True,
        mapping_status=(
            UniverseMappingStatus.AVAILABLE
            if native_ticker is not None
            else UniverseMappingStatus.UNAVAILABLE
        ),
        source_session_status="UNKNOWN",
        source_session_mode="UNKNOWN",
        technically_eligible=native_ticker is not None,
        exclusion_reasons=() if native_ticker is not None else ("MISSING_NATIVE_MAPPING",),
        raw_metadata_key="b" * 64,
    )


def _evidence(
    evidence_id: str,
    symbols: tuple[str, ...],
    *,
    start: datetime = START,
    end: datetime | None = None,
    mode: SourceSessionMode = SourceSessionMode.TWENTY_FOUR_SEVEN,
) -> SourceSessionEvidence:
    return SourceSessionEvidence(
        evidence_id=evidence_id,
        provider="Bitget",
        symbols=symbols,
        capability=SourceSessionCapabilityKind.TRADING_SCHEDULE,
        session_mode=mode,
        effective_from=start,
        effective_to=end,
        publication_time=start,
        evidence_url=f"https://www.bitget.com/{evidence_id}",
        evidence_type=SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
        confidence=SourceSessionEvidenceConfidence.VERIFIED_EXPLICIT,
        retrieved_at=datetime(2026, 9, 14, tzinfo=UTC),
        notes="test evidence",
    )


def _dataset(*records: SourceSessionEvidence) -> SourceSessionEvidenceDataset:
    return SourceSessionEvidenceDataset(
        schema_version=2,
        transformation_version="test-evidence.v1",
        retrieved_at=datetime(2026, 9, 14, tzinfo=UTC),
        evidence=records,
    )


def test_cohort_is_derived_from_full_window_explicit_evidence_and_mapping() -> None:
    dataset = _dataset(
        _evidence("full", ("RAUSDT", "RBUSDT", "RCUSDT")),
        _evidence("late", ("RDUSDT",), start=START + timedelta(hours=1)),
    )
    members = (
        _member("RDUSDT"),
        _member("RCUSDT", native_ticker=None),
        _member("RBUSDT"),
        _member("RAUSDT"),
    )
    cohort = derive_evidence_qualified_cohort(
        universe_version=VERSION,
        universe_members=members,
        evidence_dataset=dataset,
    )
    assert cohort.evaluation_start == datetime(2026, 6, 15, 20, tzinfo=UTC)
    assert cohort.evaluation_end == datetime(2026, 9, 13, 20, tzinfo=UTC)
    assert tuple(item.symbol for item in cohort.members) == ("RAUSDT", "RBUSDT")
    assert all(item.source_session_evidence_ids == ("full",) for item in cohort.members)


def test_conflicting_full_window_evidence_excludes_symbol() -> None:
    dataset = _dataset(
        _evidence("conflict-a", ("RAUSDT",), mode=SourceSessionMode.TWENTY_FOUR_SEVEN),
        _evidence("conflict-b", ("RAUSDT",), mode=SourceSessionMode.TWENTY_FOUR_FIVE),
        _evidence("clean", ("RBUSDT",)),
    )
    cohort = derive_evidence_qualified_cohort(
        universe_version=VERSION,
        universe_members=(_member("RAUSDT"), _member("RBUSDT")),
        evidence_dataset=dataset,
    )
    assert tuple(item.symbol for item in cohort.members) == ("RBUSDT",)


def test_cohort_derivation_is_deterministic_under_input_ordering() -> None:
    first = _evidence("first", ("RBUSDT", "RAUSDT"))
    second = _evidence("second", ("RAUSDT", "RBUSDT"))
    cohort_a = derive_evidence_qualified_cohort(
        universe_version=VERSION,
        universe_members=(_member("RBUSDT"), _member("RAUSDT")),
        evidence_dataset=_dataset(first, second),
    )
    cohort_b = derive_evidence_qualified_cohort(
        universe_version=VERSION,
        universe_members=(_member("RAUSDT"), _member("RBUSDT")),
        evidence_dataset=_dataset(second, first),
    )
    assert cohort_a == cohort_b


def test_fixed_window_holiday_hours_are_explicit_unknowns() -> None:
    _, report = evaluate_candle_quality(
        (),
        symbol="RAAPLUSDT",
        interval="1H",
        requested_start=START,
        requested_end=END,
        page_count=0,
        source_session_provider=CuratedBitgetSourceSessionProvider(),
    )
    assert report.expected_candles == 2160
    assert report.expected_open_interval_count == 2088
    assert report.source_session_unknown_interval_count == 72
    assert report.holiday_ambiguous_interval_count == 72
    assert report.holiday_ambiguous_timestamps[0] == datetime(2026, 6, 19, 4, tzinfo=UTC)
    assert report.holiday_ambiguous_timestamps[-1] == datetime(2026, 9, 8, 3, tzinfo=UTC)


def test_ratios_use_known_open_denominator_and_preserve_left_censoring() -> None:
    quality = SimpleNamespace(
        records_unique=100,
        observed_start=START,
        observed_end=START + timedelta(hours=99),
        quality_status=QualityStatus.WARN,
        missing_count=2,
        source_session_unknown_count=0,
        expected_open_interval_count=102,
        observed_while_expected_open_count=100,
        expected_closed_interval_count=0,
        observed_while_expected_closed_count=0,
        source_session_unknown_interval_count=6,
        observed_while_source_session_unknown_count=0,
        holiday_ambiguous_interval_count=6,
        holiday_ambiguous_timestamps=tuple(START + timedelta(hours=index) for index in range(6)),
    )
    result = build_coverage_member(
        _member("RAUSDT"),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=quality,
    )
    assert result.observed_over_known_expected == Decimal(100) / 102
    assert result.missing_over_known_expected == Decimal(2) / 102
    assert result.unknown_fraction == Decimal(6) / 108
    assert result.left_censored is True
    assert result.meets_duration_requirement is False
    assert {"return", "alpha", "sharpe"}.isdisjoint(type(result).model_fields)


def test_holiday_unknown_does_not_override_duration_and_oos_sufficiency() -> None:
    quality = SimpleNamespace(
        records_unique=2088,
        observed_start=START,
        observed_end=END - timedelta(hours=1),
        quality_status=QualityStatus.WARN,
        structural_quality_status="PASS",
        missing_count=0,
        source_session_unknown_count=72,
        expected_open_interval_count=2088,
        observed_while_expected_open_count=2088,
        expected_closed_interval_count=0,
        observed_while_expected_closed_count=0,
        source_session_unknown_interval_count=72,
        observed_while_source_session_unknown_count=0,
        holiday_ambiguous_interval_count=72,
        holiday_ambiguous_timestamps=tuple(
            START + timedelta(hours=index) for index in range(72)
        ),
    )
    result = build_coverage_member(
        _member("RAUSDT"),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=quality,
    )
    assert result.unknown_fraction == Decimal(72) / 2160
    assert result.meets_duration_requirement is True
    assert result.final_oos_feasible is True
    assert result.coverage_status == "SUFFICIENT_MINIMUM_HISTORY"


def test_missing_open_is_completeness_evidence_not_structural_failure() -> None:
    quality = SimpleNamespace(
        records_unique=2000,
        observed_start=START,
        observed_end=END - timedelta(hours=1),
        quality_status=QualityStatus.WARN,
        structural_quality_status="PASS",
        missing_count=88,
        source_session_unknown_count=0,
        expected_open_interval_count=2088,
        observed_while_expected_open_count=2000,
        expected_closed_interval_count=0,
        observed_while_expected_closed_count=0,
        source_session_unknown_interval_count=0,
        observed_while_source_session_unknown_count=0,
        holiday_ambiguous_interval_count=0,
        holiday_ambiguous_timestamps=(),
    )
    result = build_coverage_member(
        _member("RAUSDT"),
        universe_version=VERSION,
        interval="1H",
        evaluation_start=START,
        evaluation_end=END,
        verification_time=END,
        quality=quality,
    )
    assert result.missing_while_expected_open == 88
    assert result.structural_quality_status == "PASS"
    assert result.coverage_status == "SUFFICIENT_MINIMUM_HISTORY"
