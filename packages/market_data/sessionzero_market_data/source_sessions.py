from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files
from itertools import pairwise
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .calendar import NEW_YORK, XnysTradingCalendar
from .models import (
    SourceAvailabilityState,
    SourceSessionAssessment,
    SourceSessionCapability,
    SourceSessionMode,
)


class _CapabilityDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    retrieved_at: datetime
    capabilities: tuple[SourceSessionCapability, ...]

    def model_post_init(self, __context: object) -> None:
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("dataset retrieved_at must be timezone-aware")


def load_bitget_source_capabilities() -> tuple[SourceSessionCapability, ...]:
    resource = files("sessionzero_market_data").joinpath("data/bitget_source_sessions.json")
    dataset = _CapabilityDataset.model_validate_json(resource.read_text(encoding="utf-8"))
    return dataset.capabilities


class CuratedBitgetSourceSessionProvider:
    """Point-in-time source eligibility from cited, version-controlled evidence."""

    def __init__(
        self,
        capabilities: tuple[SourceSessionCapability, ...] | None = None,
        calendar: XnysTradingCalendar | None = None,
    ) -> None:
        self.capabilities = (
            capabilities if capabilities is not None else load_bitget_source_capabilities()
        )
        for symbol in {item.symbol for item in self.capabilities}:
            entries = sorted(
                (item for item in self.capabilities if item.symbol == symbol),
                key=lambda item: item.effective_from,
            )
            for previous, current in pairwise(entries):
                if previous.effective_to is None or previous.effective_to > current.effective_from:
                    raise ValueError(f"overlapping source-session capabilities for {symbol}")
        self._calendar = calendar or XnysTradingCalendar()

    def _capability_at(self, symbol: str, timestamp: datetime) -> SourceSessionCapability | None:
        eligible = [
            item
            for item in self.capabilities
            if item.symbol in {"*", symbol}
            and item.effective_from <= timestamp
            and (item.effective_to is None or timestamp < item.effective_to)
        ]
        if not eligible:
            return None
        return max(eligible, key=lambda item: (item.symbol == symbol, item.effective_from))

    def session_at(self, symbol: str, timestamp: datetime) -> SourceSessionAssessment:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        timestamp = timestamp.astimezone(UTC)
        symbol = symbol.upper()
        capability = self._capability_at(symbol, timestamp)
        if capability is None:
            return SourceSessionAssessment(
                symbol=symbol,
                as_of=timestamp,
                availability=SourceAvailabilityState.UNKNOWN,
                session_mode=SourceSessionMode.UNKNOWN,
                reason="no cited capability record covers this symbol and timestamp",
            )
        common = {
            "symbol": symbol,
            "as_of": timestamp,
            "session_mode": capability.session_mode,
            "capability_effective_from": capability.effective_from,
            "evidence_url": capability.evidence_url,
        }
        if capability.session_mode == SourceSessionMode.TWENTY_FOUR_SEVEN:
            if self._calendar.session_at(timestamp).local_date_is_holiday:
                return SourceSessionAssessment(
                    **common,
                    availability=SourceAvailabilityState.UNKNOWN,
                    reason="the rollout says holiday weekend-session opening may be postponed",
                )
            return SourceSessionAssessment(
                **common,
                availability=SourceAvailabilityState.EXPECTED_OPEN,
                reason="cited symbol-specific 24/7 capability is effective",
            )
        if capability.session_mode == SourceSessionMode.TWENTY_FOUR_FIVE:
            reference = self._calendar.session_at(timestamp)
            local = timestamp.astimezone(NEW_YORK)
            if reference.local_date_is_holiday:
                return SourceSessionAssessment(
                    **common,
                    availability=SourceAvailabilityState.UNKNOWN,
                    reason="official 24/5 guidance says holiday access may be limited",
                )
            if local.weekday() >= 5:
                if capability.symbol == "*":
                    return SourceSessionAssessment(
                        **common,
                        availability=SourceAvailabilityState.UNKNOWN,
                        reason="baseline 24/5 evidence does not identify all weekend exceptions",
                    )
                return SourceSessionAssessment(
                    **common,
                    availability=SourceAvailabilityState.EXPECTED_CLOSED,
                    reason="later rollout evidence establishes this pre-24/7 period",
                )
            return SourceSessionAssessment(
                **common,
                availability=SourceAvailabilityState.EXPECTED_OPEN,
                reason="cited 24/5 capability covers this weekday",
            )
        return SourceSessionAssessment(
            **common,
            availability=SourceAvailabilityState.UNKNOWN,
            reason="capability does not establish precise expected availability",
        )
