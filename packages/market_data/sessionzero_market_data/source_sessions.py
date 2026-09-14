from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files

from .calendar import NEW_YORK, XnysTradingCalendar
from .models import (
    SourceAvailabilityState,
    SourceSessionAmbiguityKind,
    SourceSessionAssessment,
    SourceSessionCapability,
    SourceSessionCapabilityKind,
    SourceSessionEvidence,
    SourceSessionEvidenceConfidence,
    SourceSessionEvidenceDataset,
    SourceSessionEvidenceType,
    SourceSessionMode,
    SourceSessionResolutionStatus,
)

SOURCE_SESSION_TRANSFORMATION_VERSION = "bitget_source_sessions.v2"


def load_bitget_source_session_evidence() -> SourceSessionEvidenceDataset:
    resource = files("sessionzero_market_data").joinpath("data/bitget_source_sessions.json")
    dataset = SourceSessionEvidenceDataset.model_validate_json(resource.read_text(encoding="utf-8"))
    if dataset.transformation_version != SOURCE_SESSION_TRANSFORMATION_VERSION:
        raise ValueError("unsupported source-session transformation version")
    return dataset


def load_bitget_source_capabilities() -> tuple[SourceSessionCapability, ...]:
    """Compatibility view expanded from the normalized evidence records."""
    capabilities: list[SourceSessionCapability] = []
    for record in load_bitget_source_session_evidence().evidence:
        if (
            not record.symbols
            or record.evidence_type == SourceSessionEvidenceType.CURRENT_METADATA
            or record.confidence == SourceSessionEvidenceConfidence.AMBIGUOUS_SCOPE
        ):
            continue
        for symbol in record.symbols:
            capabilities.append(
                SourceSessionCapability(
                    symbol=symbol,
                    effective_from=record.effective_from,
                    effective_to=record.effective_to,
                    session_mode=record.session_mode,
                    source=record.provider,
                    evidence_url=record.evidence_url,
                    verified_at=record.retrieved_at,
                    notes=record.notes,
                )
            )
    return tuple(capabilities)


def _legacy_evidence(
    capabilities: tuple[SourceSessionCapability, ...],
) -> tuple[SourceSessionEvidence, ...]:
    return tuple(
        SourceSessionEvidence(
            evidence_id=f"legacy.{index}",
            provider=item.source,
            symbols=(item.symbol,),
            capability=SourceSessionCapabilityKind.TRADING_SCHEDULE,
            session_mode=item.session_mode,
            effective_from=item.effective_from,
            effective_to=item.effective_to,
            publication_time=None,
            evidence_url=item.evidence_url,
            evidence_type=SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE,
            confidence=SourceSessionEvidenceConfidence.VERIFIED_EXPLICIT,
            retrieved_at=item.verified_at,
            notes=item.notes,
        )
        for index, item in enumerate(capabilities)
    )


def _precedence(record: SourceSessionEvidence) -> tuple[int, float]:
    capability_rank = 4 if record.capability == SourceSessionCapabilityKind.SUSPENSION else 0
    evidence_rank = {
        SourceSessionEvidenceType.SYMBOL_BATCH_CHANGE: 3,
        SourceSessionEvidenceType.DATED_ENUMERATED_STATUS: 2,
        SourceSessionEvidenceType.GENERAL_PRODUCT_RULE: 1,
        SourceSessionEvidenceType.CURRENT_METADATA: 0,
        SourceSessionEvidenceType.AMBIGUOUS_NOTICE: 0,
    }[record.evidence_type]
    return capability_rank + evidence_rank, record.effective_from.timestamp()


class CuratedBitgetSourceSessionProvider:
    """Point-in-time source availability resolved from cited version-controlled evidence."""

    def __init__(
        self,
        capabilities: tuple[SourceSessionCapability, ...] | None = None,
        calendar: XnysTradingCalendar | None = None,
        *,
        evidence: tuple[SourceSessionEvidence, ...] | None = None,
        transformation_version: str = SOURCE_SESSION_TRANSFORMATION_VERSION,
    ) -> None:
        if capabilities is not None and evidence is not None:
            raise ValueError("provide capabilities or evidence, not both")
        if evidence is not None:
            self.evidence = evidence
        elif capabilities is not None:
            self.evidence = _legacy_evidence(capabilities)
        else:
            dataset = load_bitget_source_session_evidence()
            self.evidence = dataset.evidence
            transformation_version = dataset.transformation_version
        self.transformation_version = transformation_version
        self._calendar = calendar or XnysTradingCalendar()

    def _candidates(self, symbol: str, timestamp: datetime) -> tuple[SourceSessionEvidence, ...]:
        return tuple(
            record
            for record in self.evidence
            if record.symbols
            and record.evidence_type != SourceSessionEvidenceType.CURRENT_METADATA
            and record.confidence != SourceSessionEvidenceConfidence.AMBIGUOUS_SCOPE
            and ("*" in record.symbols or symbol in record.symbols)
            and record.effective_from <= timestamp
            and (record.effective_to is None or timestamp < record.effective_to)
        )

    def _resolve(
        self, symbol: str, timestamp: datetime
    ) -> tuple[tuple[SourceSessionEvidence, ...], SourceSessionResolutionStatus]:
        candidates = self._candidates(symbol, timestamp)
        if not candidates:
            return (), SourceSessionResolutionStatus.NO_EVIDENCE
        highest = max(_precedence(record) for record in candidates)
        winners = tuple(
            sorted(
                (record for record in candidates if _precedence(record) == highest),
                key=lambda record: record.evidence_id,
            )
        )
        outcomes = {(record.capability, record.session_mode) for record in winners}
        if len(outcomes) != 1:
            return winners, SourceSessionResolutionStatus.CONFLICT
        return winners, SourceSessionResolutionStatus.RESOLVED

    def session_at(self, symbol: str, timestamp: datetime) -> SourceSessionAssessment:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        timestamp = timestamp.astimezone(UTC)
        symbol = symbol.upper()
        winners, resolution = self._resolve(symbol, timestamp)
        evidence_ids = tuple(record.evidence_id for record in winners)
        evidence_urls = tuple(sorted({record.evidence_url for record in winners}))
        if resolution == SourceSessionResolutionStatus.NO_EVIDENCE:
            return SourceSessionAssessment(
                symbol=symbol,
                as_of=timestamp,
                availability=SourceAvailabilityState.UNKNOWN,
                session_mode=SourceSessionMode.UNKNOWN,
                transformation_version=self.transformation_version,
                resolution_status=resolution,
                ambiguity_kind=SourceSessionAmbiguityKind.NO_EVIDENCE,
                reason="no cited historical evidence covers this symbol and timestamp",
            )
        if resolution == SourceSessionResolutionStatus.CONFLICT:
            return SourceSessionAssessment(
                symbol=symbol,
                as_of=timestamp,
                availability=SourceAvailabilityState.UNKNOWN,
                session_mode=SourceSessionMode.UNKNOWN,
                evidence_ids=evidence_ids,
                evidence_urls=evidence_urls,
                transformation_version=self.transformation_version,
                resolution_status=resolution,
                ambiguity_kind=SourceSessionAmbiguityKind.CONFLICT,
                reason="highest-precedence historical evidence has conflicting outcomes",
            )
        capability = winners[0]
        common = {
            "symbol": symbol,
            "as_of": timestamp,
            "session_mode": capability.session_mode,
            "capability_effective_from": capability.effective_from,
            "evidence_url": evidence_urls[0],
            "evidence_ids": evidence_ids,
            "evidence_urls": evidence_urls,
            "transformation_version": self.transformation_version,
            "resolution_status": resolution,
        }
        if capability.capability == SourceSessionCapabilityKind.SUSPENSION:
            return SourceSessionAssessment(
                **common,
                availability=SourceAvailabilityState.EXPECTED_CLOSED,
                reason="explicit symbol-scoped suspension evidence is effective",
            )
        if capability.session_mode == SourceSessionMode.TWENTY_FOUR_SEVEN:
            if self._calendar.session_at(timestamp).local_date_is_holiday:
                return SourceSessionAssessment(
                    **common,
                    availability=SourceAvailabilityState.UNKNOWN,
                    ambiguity_kind=SourceSessionAmbiguityKind.HOLIDAY_QUALIFIED,
                    reason="official weekend evidence says holiday opening may be postponed",
                )
            return SourceSessionAssessment(
                **common,
                availability=SourceAvailabilityState.EXPECTED_OPEN,
                reason="dated symbol-set 24/7 evidence is effective",
            )
        if capability.session_mode == SourceSessionMode.TWENTY_FOUR_FIVE:
            reference = self._calendar.session_at(timestamp)
            local = timestamp.astimezone(NEW_YORK)
            if reference.local_date_is_holiday:
                return SourceSessionAssessment(
                    **common,
                    availability=SourceAvailabilityState.UNKNOWN,
                    ambiguity_kind=SourceSessionAmbiguityKind.HOLIDAY_QUALIFIED,
                    reason="official 24/5 guidance says holiday access may be limited",
                )
            if local.weekday() >= 5:
                return SourceSessionAssessment(
                    **common,
                    availability=SourceAvailabilityState.UNKNOWN,
                    ambiguity_kind=SourceSessionAmbiguityKind.WEEKEND_SCOPE,
                    reason="general 24/5 evidence does not prove symbol-level weekend closure",
                )
            return SourceSessionAssessment(
                **common,
                availability=SourceAvailabilityState.EXPECTED_OPEN,
                reason="cited 24/5 capability covers this weekday",
            )
        return SourceSessionAssessment(
            **common,
            availability=SourceAvailabilityState.UNKNOWN,
            ambiguity_kind=SourceSessionAmbiguityKind.IMPRECISE_SCHEDULE,
            reason="evidence does not establish precise expected availability",
        )
