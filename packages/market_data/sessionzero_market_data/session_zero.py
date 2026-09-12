from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from .interfaces import TradingCalendarProvider
from .models import SessionZeroContext, SessionZeroState, SourceAvailabilityState


def classify_session_zero(
    timestamp: datetime,
    *,
    calendar: TradingCalendarProvider,
    source_states: Sequence[SourceAvailabilityState],
) -> SessionZeroContext:
    reference = calendar.session_at(timestamp)
    states = tuple(source_states)
    if reference.cash_market_open:
        state = SessionZeroState.INACTIVE
    elif SourceAvailabilityState.EXPECTED_OPEN in states:
        state = SessionZeroState.ACTIVE
    elif not states or SourceAvailabilityState.UNKNOWN in states:
        state = SessionZeroState.UNKNOWN
    else:
        state = SessionZeroState.INACTIVE
    return SessionZeroContext(
        as_of=reference.as_of,
        cash_market_open=reference.cash_market_open,
        session_zero_state=state,
        previous_cash_close=reference.previous_cash_close,
        next_cash_open=reference.next_cash_open,
        reference_session_date=reference.reference_session_date,
        source_states=states,
    )
