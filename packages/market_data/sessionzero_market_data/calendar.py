from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import exchange_calendars
import pandas as pd

from .models import CashSessionContext

NEW_YORK = ZoneInfo("America/New_York")
REGULAR_CLOSE = time(16, 0)


def _utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return timestamp.astimezone(UTC)


def _datetime(timestamp: pd.Timestamp) -> datetime:
    return timestamp.to_pydatetime().astimezone(UTC)


class XnysTradingCalendar:
    """DST-safe NYSE regular-session semantics backed by exchange-calendars."""

    def __init__(self) -> None:
        self._calendar = exchange_calendars.get_calendar("XNYS")

    def _is_session(self, value: date) -> bool:
        return bool(self._calendar.is_session(pd.Timestamp(value)))

    def _session_open(self, value: date) -> datetime:
        return _datetime(self._calendar.session_open(pd.Timestamp(value)))

    def _session_close(self, value: date) -> datetime:
        return _datetime(self._calendar.session_close(pd.Timestamp(value)))

    def _session_on_or_after(self, value: date) -> date:
        session = self._calendar.date_to_session(pd.Timestamp(value), direction="next")
        return session.date()

    def _session_on_or_before(self, value: date) -> date:
        session = self._calendar.date_to_session(pd.Timestamp(value), direction="previous")
        return session.date()

    def _next_session(self, value: date) -> date:
        return self._calendar.next_session(pd.Timestamp(value)).date()

    def _previous_session(self, value: date) -> date:
        return self._calendar.previous_session(pd.Timestamp(value)).date()

    def session_on(self, session_date: date) -> CashSessionContext:
        """Return an exact scheduled session; never move a holiday to another date."""
        if not self._is_session(session_date):
            raise ValueError("requested date is not an XNYS session")
        return self.session_at(self._session_open(session_date))

    def session_at(self, timestamp: datetime) -> CashSessionContext:
        timestamp = _utc(timestamp)
        local_date = timestamp.astimezone(NEW_YORK).date()
        local_date_is_session = self._is_session(local_date)
        today_open = self._session_open(local_date) if local_date_is_session else None
        today_close = self._session_close(local_date) if local_date_is_session else None
        cash_market_open = bool(
            today_open is not None
            and today_close is not None
            and today_open <= timestamp < today_close
        )

        if cash_market_open or (today_open is not None and timestamp < today_open):
            reference_session_date = local_date
        elif local_date_is_session:
            reference_session_date = self._next_session(local_date)
        else:
            reference_session_date = self._session_on_or_after(local_date)

        regular_open = self._session_open(reference_session_date)
        regular_close = self._session_close(reference_session_date)

        if today_close is not None and today_close <= timestamp:
            previous_cash_close = today_close
        else:
            previous_date = (
                self._previous_session(local_date)
                if local_date_is_session
                else self._session_on_or_before(local_date)
            )
            previous_cash_close = self._session_close(previous_date)

        if today_open is not None and timestamp < today_open:
            next_cash_open = today_open
        elif local_date_is_session:
            next_cash_open = self._session_open(self._next_session(local_date))
        else:
            next_cash_open = self._session_open(self._session_on_or_after(local_date))

        close_local = (
            today_close.astimezone(NEW_YORK).time().replace(tzinfo=None)
            if today_close is not None
            else None
        )
        return CashSessionContext(
            as_of=timestamp,
            cash_market_open=cash_market_open,
            reference_session_date=reference_session_date,
            regular_open=regular_open,
            regular_close=regular_close,
            previous_cash_close=previous_cash_close,
            next_cash_open=next_cash_open,
            local_date_is_session=local_date_is_session,
            local_date_is_holiday=local_date.weekday() < 5 and not local_date_is_session,
            early_close=close_local is not None and close_local < REGULAR_CLOSE,
        )
