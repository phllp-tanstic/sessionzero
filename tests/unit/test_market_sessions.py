from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sessionzero_market_data import (
    CuratedBitgetSourceSessionProvider,
    SessionZeroState,
    SourceAvailabilityState,
    SourceSessionCapabilityKind,
    SourceSessionEvidence,
    SourceSessionEvidenceConfidence,
    SourceSessionEvidenceType,
    SourceSessionMode,
    SourceSessionResolutionStatus,
    XnysTradingCalendar,
    classify_session_zero,
    load_bitget_source_capabilities,
    load_bitget_source_session_evidence,
)


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def test_normal_cash_session_and_adjacent_boundaries() -> None:
    context = XnysTradingCalendar().session_at(utc("2026-06-17T15:00:00Z"))
    assert context.cash_market_open is True
    assert context.reference_session_date == date(2026, 6, 17)
    assert context.regular_open == utc("2026-06-17T13:30:00Z")
    assert context.regular_close == utc("2026-06-17T20:00:00Z")
    assert context.previous_cash_close == utc("2026-06-16T20:00:00Z")
    assert context.next_cash_open == utc("2026-06-18T13:30:00Z")


def test_weekend_uses_previous_close_and_next_open() -> None:
    context = XnysTradingCalendar().session_at(utc("2026-06-20T15:00:00Z"))
    assert context.cash_market_open is False
    assert context.local_date_is_session is False
    assert context.local_date_is_holiday is False
    assert context.previous_cash_close == utc("2026-06-18T20:00:00Z")
    assert context.next_cash_open == utc("2026-06-22T13:30:00Z")


def test_juneteenth_2026_is_a_full_day_cash_holiday() -> None:
    context = XnysTradingCalendar().session_at(utc("2026-06-19T15:00:00Z"))
    assert context.cash_market_open is False
    assert context.local_date_is_holiday is True
    assert context.previous_cash_close == utc("2026-06-18T20:00:00Z")
    assert context.next_cash_open == utc("2026-06-22T13:30:00Z")


def test_dst_transition_changes_utc_open_without_changing_local_open() -> None:
    before = XnysTradingCalendar().session_at(utc("2026-03-06T15:00:00Z"))
    after = XnysTradingCalendar().session_at(utc("2026-03-09T14:00:00Z"))
    assert before.regular_open == utc("2026-03-06T14:30:00Z")
    assert after.regular_open == utc("2026-03-09T13:30:00Z")
    assert before.cash_market_open is True
    assert after.cash_market_open is True


def test_early_close_and_post_close_navigation() -> None:
    calendar = XnysTradingCalendar()
    during = calendar.session_at(utc("2026-11-27T17:00:00Z"))
    after = calendar.session_at(utc("2026-11-27T19:00:00Z"))
    assert during.early_close is True
    assert during.regular_close == utc("2026-11-27T18:00:00Z")
    assert after.cash_market_open is False
    assert after.early_close is True
    assert after.previous_cash_close == utc("2026-11-27T18:00:00Z")
    assert after.next_cash_open == utc("2026-11-30T14:30:00Z")
    assert after.reference_session_date == date(2026, 11, 30)


def test_curated_capabilities_have_machine_readable_provenance() -> None:
    dataset = load_bitget_source_session_evidence()
    capabilities = load_bitget_source_capabilities()
    assert dataset.schema_version == 2
    assert dataset.transformation_version == "bitget_source_sessions.v2"
    assert len(dataset.evidence) == 8
    assert {len(item.symbols) for item in dataset.evidence} >= {0, 14, 21, 22, 61, 93}
    assert all(item.evidence_url.startswith("https://www.bitget.com/") for item in capabilities)
    assert all(item.verified_at.tzinfo is not None for item in capabilities)


def test_known_24_5_period_and_unknown_history() -> None:
    provider = CuratedBitgetSourceSessionProvider()
    weekday = provider.session_at("RAALUSDT", utc("2026-06-24T12:00:00Z"))
    weekend = provider.session_at("RMRNAUSDT", utc("2026-06-27T16:00:00Z"))
    generic_weekend = provider.session_at("RAALUSDT", utc("2026-06-27T16:00:00Z"))
    unknown = provider.session_at("RAALUSDT", utc("2026-06-22T12:00:00Z"))
    assert weekday.session_mode == SourceSessionMode.TWENTY_FOUR_FIVE
    assert weekday.availability == SourceAvailabilityState.EXPECTED_OPEN
    assert weekend.availability == SourceAvailabilityState.UNKNOWN
    assert generic_weekend.availability == SourceAvailabilityState.UNKNOWN
    assert unknown.availability == SourceAvailabilityState.UNKNOWN


def test_holiday_availability_is_unknown_under_general_24_5_evidence() -> None:
    assessment = CuratedBitgetSourceSessionProvider().session_at(
        "RAALUSDT", utc("2026-07-03T16:00:00Z")
    )
    assert assessment.session_mode == SourceSessionMode.TWENTY_FOUR_FIVE
    assert assessment.availability == SourceAvailabilityState.UNKNOWN

    rollout_holiday = CuratedBitgetSourceSessionProvider().session_at(
        "RMRNAUSDT", utc("2026-09-07T16:00:00Z")
    )
    assert rollout_holiday.session_mode == SourceSessionMode.TWENTY_FOUR_SEVEN
    assert rollout_holiday.availability == SourceAvailabilityState.UNKNOWN


def test_symbol_specific_24_7_boundary_is_point_in_time() -> None:
    provider = CuratedBitgetSourceSessionProvider()
    before = provider.session_at("RMRNAUSDT", utc("2026-07-17T03:39:59Z"))
    boundary = provider.session_at("RMRNAUSDT", utc("2026-07-17T03:40:00Z"))
    weekend_before = provider.session_at("RMRNAUSDT", utc("2026-07-11T16:00:00Z"))
    weekend_after = provider.session_at("RMRNAUSDT", utc("2026-07-18T16:00:00Z"))
    assert before.session_mode == SourceSessionMode.TWENTY_FOUR_FIVE
    assert boundary.session_mode == SourceSessionMode.TWENTY_FOUR_SEVEN
    assert weekend_before.availability == SourceAvailabilityState.UNKNOWN
    assert weekend_after.availability == SourceAvailabilityState.EXPECTED_OPEN


def test_first_batch_and_later_batch_boundaries_are_not_projected_backward() -> None:
    provider = CuratedBitgetSourceSessionProvider()
    aapl_before = provider.session_at("RAAPLUSDT", utc("2026-06-12T13:20:59Z"))
    aapl_at = provider.session_at("RAAPLUSDT", utc("2026-06-12T13:21:00Z"))
    abnb_before = provider.session_at("RABNBUSDT", utc("2026-08-14T09:19:59Z"))
    abnb_at = provider.session_at("RABNBUSDT", utc("2026-08-14T09:20:00Z"))
    assert aapl_before.availability == SourceAvailabilityState.UNKNOWN
    assert aapl_at.availability == SourceAvailabilityState.EXPECTED_OPEN
    assert aapl_at.evidence_ids == ("bitget.2026-06-12.weekend-batch-21",)
    assert aapl_at.evidence_urls == ("https://www.bitget.com/support/articles/12560603885756",)
    assert aapl_at.transformation_version == "bitget_source_sessions.v2"
    assert abnb_before.session_mode == SourceSessionMode.TWENTY_FOUR_FIVE
    assert abnb_at.availability == SourceAvailabilityState.EXPECTED_OPEN


def _evidence(
    evidence_id: str,
    *,
    mode: SourceSessionMode,
    evidence_type: SourceSessionEvidenceType,
    effective: str = "2026-06-12T00:00:00Z",
) -> SourceSessionEvidence:
    return SourceSessionEvidence(
        evidence_id=evidence_id,
        provider="Bitget",
        symbols=("RTESTUSDT",),
        capability=SourceSessionCapabilityKind.TRADING_SCHEDULE,
        session_mode=mode,
        effective_from=utc(effective),
        publication_time=(
            None if evidence_type == SourceSessionEvidenceType.CURRENT_METADATA else utc(effective)
        ),
        evidence_url=f"https://www.bitget.com/{evidence_id}",
        evidence_type=evidence_type,
        confidence=SourceSessionEvidenceConfidence.VERIFIED_EXPLICIT,
        retrieved_at=utc("2026-09-14T00:00:00Z"),
        notes="deterministic evidence",
    )


def test_symbol_batch_precedes_general_rule() -> None:
    general = _evidence(
        "general",
        mode=SourceSessionMode.TWENTY_FOUR_FIVE,
        evidence_type=SourceSessionEvidenceType.GENERAL_PRODUCT_RULE,
    ).model_copy(update={"symbols": ("*",)})
    batch = _evidence(
        "batch",
        mode=SourceSessionMode.TWENTY_FOUR_SEVEN,
        evidence_type=SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
    )
    result = CuratedBitgetSourceSessionProvider(evidence=(general, batch)).session_at(
        "RTESTUSDT", utc("2026-06-13T12:00:00Z")
    )
    assert result.session_mode == SourceSessionMode.TWENTY_FOUR_SEVEN
    assert result.evidence_ids == ("batch",)


def test_equal_precedence_conflict_is_visible_and_unknown() -> None:
    first = _evidence(
        "conflict-a",
        mode=SourceSessionMode.TWENTY_FOUR_FIVE,
        evidence_type=SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
    )
    second = _evidence(
        "conflict-b",
        mode=SourceSessionMode.TWENTY_FOUR_SEVEN,
        evidence_type=SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
    )
    result = CuratedBitgetSourceSessionProvider(evidence=(first, second)).session_at(
        "RTESTUSDT", utc("2026-06-13T12:00:00Z")
    )
    assert result.availability == SourceAvailabilityState.UNKNOWN
    assert result.resolution_status == SourceSessionResolutionStatus.CONFLICT
    assert result.evidence_ids == ("conflict-a", "conflict-b")


def test_current_metadata_is_never_used_as_historical_evidence() -> None:
    current = _evidence(
        "current",
        mode=SourceSessionMode.TWENTY_FOUR_SEVEN,
        evidence_type=SourceSessionEvidenceType.CURRENT_METADATA,
    )
    result = CuratedBitgetSourceSessionProvider(evidence=(current,)).session_at(
        "RTESTUSDT", utc("2026-09-14T12:00:00Z")
    )
    assert result.availability == SourceAvailabilityState.UNKNOWN
    assert result.resolution_status == SourceSessionResolutionStatus.NO_EVIDENCE


def test_ambiguous_holiday_notice_does_not_infer_a_wildcard_closure() -> None:
    result = CuratedBitgetSourceSessionProvider().session_at(
        "RAALUSDT", utc("2026-07-02T18:00:00Z")
    )
    assert result.availability == SourceAvailabilityState.EXPECTED_OPEN


def test_suspension_evidence_cannot_use_wildcard_scope() -> None:
    with pytest.raises(ValueError, match="must enumerate affected symbols"):
        SourceSessionEvidence(
            evidence_id="wildcard-suspension",
            provider="Bitget",
            symbols=("*",),
            capability=SourceSessionCapabilityKind.SUSPENSION,
            session_mode=SourceSessionMode.UNKNOWN,
            effective_from=utc("2026-07-03T00:00:00Z"),
            effective_to=utc("2026-07-04T00:00:00Z"),
            publication_time=utc("2026-07-02T00:00:00Z"),
            evidence_url="https://www.bitget.com/wildcard-suspension",
            evidence_type=SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
            confidence=SourceSessionEvidenceConfidence.VERIFIED_EXPLICIT,
            retrieved_at=utc("2026-09-14T00:00:00Z"),
            notes="invalid unscoped closure",
        )


def test_session_zero_requires_a_known_open_source() -> None:
    calendar = XnysTradingCalendar()
    timestamp = utc("2026-06-20T15:00:00Z")
    active = classify_session_zero(
        timestamp,
        calendar=calendar,
        source_states=[SourceAvailabilityState.EXPECTED_OPEN],
    )
    unknown = classify_session_zero(
        timestamp,
        calendar=calendar,
        source_states=[SourceAvailabilityState.UNKNOWN],
    )
    inactive = classify_session_zero(
        timestamp,
        calendar=calendar,
        source_states=[SourceAvailabilityState.EXPECTED_CLOSED],
    )
    assert active.session_zero_state == SessionZeroState.ACTIVE
    assert unknown.session_zero_state == SessionZeroState.UNKNOWN
    assert inactive.session_zero_state == SessionZeroState.INACTIVE


def test_session_zero_is_inactive_while_cash_market_is_open() -> None:
    context = classify_session_zero(
        utc("2026-06-17T15:00:00Z"),
        calendar=XnysTradingCalendar(),
        source_states=[SourceAvailabilityState.EXPECTED_OPEN],
    )
    assert context.cash_market_open is True
    assert context.session_zero_state == SessionZeroState.INACTIVE
