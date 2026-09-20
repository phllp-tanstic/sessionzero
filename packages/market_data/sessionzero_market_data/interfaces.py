from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from .models import CashSessionContext, SourceSessionAssessment


class TradingCalendarProvider(Protocol):
    def session_at(self, timestamp: datetime) -> CashSessionContext: ...

    def session_on(self, session_date: date) -> CashSessionContext: ...


class SourceSessionProvider(Protocol):
    def session_at(self, symbol: str, timestamp: datetime) -> SourceSessionAssessment: ...
