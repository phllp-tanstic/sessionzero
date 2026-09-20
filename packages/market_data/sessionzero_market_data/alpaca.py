"""Read-only historical SIP adapter; credentials come exclusively from the environment."""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx
from pydantic import ValidationError
from sessionzero_schemas import EvidenceQualifiedCohort

from .calendar import NEW_YORK, XnysTradingCalendar
from .interfaces import TradingCalendarProvider
from .native import (
    NativeCandle,
    NativeCapability,
    NativeDataError,
    NativeHistory,
    NativeInstrument,
    NativePage,
    NativeTarget,
    mapped_instruments,
    session_target,
    utc,
)

SAFE_HEADERS = (
    "x-request-id",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "retry-after",
    "date",
)


def _invalid_json_constant(value: str):
    raise ValueError("non-finite JSON number")


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class AlpacaNativeEquityProvider:
    def __init__(
        self,
        cohort: EvidenceQualifiedCohort,
        *,
        calendar: TradingCalendarProvider | None = None,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        page_limit: int = 10000,
        max_pages: int = 100,
        max_retries: int = 3,
    ):
        if not 1 <= page_limit <= 10000 or not 1 <= max_pages <= 1000 or not 0 <= max_retries <= 5:
            raise ValueError("invalid request bounds")
        self._instruments = {i.reality_symbol: i for i in mapped_instruments(cohort)}
        self.calendar = calendar or XnysTradingCalendar()
        self.clock, self.sleep = clock, sleep
        self.page_limit, self.max_pages, self.max_retries = page_limit, max_pages, max_retries
        self._client = httpx.Client(transport=transport, timeout=20, follow_redirects=False)
        self._state = NativeCapability.GATED
        self._last_request: float | None = None
        self.telemetry = {"requests": 0, "retries": 0, "rate_limits": 0}
        self.attempts: list[dict] = []  # safe response metadata, including unsuccessful attempts

    def close(self) -> None:
        self._client.close()

    def health(self) -> NativeCapability:
        if not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"):
            return NativeCapability.GATED
        return self._state  # credentials alone never prove access

    def get_instrument(self, reality_symbol: str) -> NativeInstrument:
        try:
            return self._instruments[reality_symbol]
        except KeyError:
            raise NativeDataError("ACCEPTED_MAPPING_REQUIRED") from None

    def _delay(self, response: httpx.Response, attempt: int) -> float:
        delay = min(2**attempt, 30)
        retry_after = response.headers.get("retry-after")
        try:
            if retry_after:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = (parsedate_to_datetime(retry_after) - utc(self.clock())).total_seconds()
            elif response.status_code == 429 and response.headers.get("x-ratelimit-reset"):
                delay = float(response.headers["x-ratelimit-reset"]) - utc(self.clock()).timestamp()
        except (ValueError, TypeError, OverflowError):
            raise NativeDataError("INVALID_RETRY_DELAY", NativeCapability.DEGRADED) from None
        if not math.isfinite(delay) or delay > 60:
            # Do not truncate a server-required delay and retry prematurely.
            raise NativeDataError("RETRY_DELAY_EXCEEDS_BUDGET", NativeCapability.DEGRADED)
        return max(0.31, delay)

    def _request(self, endpoint: str, params: dict) -> NativePage:
        key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
        if not key or not secret:
            raise NativeDataError("MISSING_ALPACA_CREDENTIALS", NativeCapability.GATED)
        for attempt in range(self.max_retries + 1):
            if self._last_request is not None:
                self.sleep(max(0, 0.31 - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            self.telemetry["requests"] += 1
            try:
                response = self._client.get(
                    endpoint,
                    params=params,
                    headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
                )
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise NativeDataError(
                        "NETWORK_RETRIES_EXHAUSTED", NativeCapability.DEGRADED
                    ) from None
                self.telemetry["retries"] += 1
                self.sleep(min(2**attempt, 30))
                continue
            headers = {
                name: response.headers[name] for name in SAFE_HEADERS if name in response.headers
            }
            received = utc(self.clock())
            self.attempts.append(
                {
                    "status": response.status_code,
                    "headers": headers,
                    "ingestion_time": received.isoformat(),
                }
            )
            if response.status_code == 200:
                return NativePage(endpoint, dict(params), received, headers, response.text)
            if response.status_code in (401, 403):
                raise NativeDataError("AUTHENTICATION_OR_ENTITLEMENT", NativeCapability.GATED)
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                self.telemetry["rate_limits"] += response.status_code == 429
                if attempt < self.max_retries:
                    self.telemetry["retries"] += 1
                    self.sleep(self._delay(response, attempt))
                    continue
                raise NativeDataError("HTTP_RETRIES_EXHAUSTED", NativeCapability.DEGRADED)
            raise NativeDataError(f"PROVIDER_HTTP_{response.status_code}")
        raise AssertionError("bounded retry exhausted")

    def get_candles(self, reality_symbol: str, start: datetime, end: datetime) -> NativeHistory:
        instrument = self.get_instrument(reality_symbol)
        start, end = utc(start), utc(end)
        if not start < end or end - start > timedelta(days=90):
            raise ValueError("history window must be positive and at most 90 days")
        if end > utc(self.clock()) - timedelta(minutes=15, seconds=5):
            raise NativeDataError("HISTORICAL_SIP_EMBARGO", NativeCapability.GATED)
        try:
            result = self._history(instrument, start, end)
        except NativeDataError as exc:
            self._state = exc.state
            raise
        self._state = NativeCapability.AVAILABLE
        return result

    def _history(
        self, instrument: NativeInstrument, start: datetime, end: datetime, *, request_page=None
    ) -> NativeHistory:
        endpoint = (
            "https://data.alpaca.markets/v2/stocks/"
            + quote(instrument.native_ticker, safe="")
            + "/bars"
        )
        params = {
            "timeframe": "1Min",
            "feed": "sip",
            "adjustment": "raw",
            "asof": "-",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "sort": "asc",
            "limit": self.page_limit,
        }
        pages, candles = [], []
        tokens: set[str] = set()
        previous: datetime | None = None
        clipped = 0
        for index in range(self.max_pages):
            page = (request_page or self._request)(endpoint, params)
            pages.append(page)
            try:
                payload = json.loads(
                    page.body,
                    parse_float=Decimal,
                    parse_constant=_invalid_json_constant,
                    object_pairs_hook=_unique_object,
                )
                if (
                    not isinstance(payload, dict)
                    or payload.get("symbol") != instrument.native_ticker
                    or "bars" not in payload
                    or "next_page_token" not in payload
                ):
                    raise ValueError("invalid envelope")
                rows = payload["bars"]
                if rows is None:
                    rows = []  # documented empty history representation
                token = payload["next_page_token"]
                if not isinstance(rows, list) or len(rows) > self.page_limit:
                    raise ValueError("invalid bars")
                if token is not None and (not isinstance(token, str) or not token):
                    raise ValueError("invalid token")
                for row in rows:
                    if not isinstance(row, dict) or not isinstance(row.get("t"), str):
                        raise ValueError("invalid bar")
                    if not re.fullmatch(
                        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00(?:\.0{1,9})?(?:Z|[+-]\d{2}:\d{2})",
                        row["t"],
                    ):
                        raise ValueError("invalid RFC3339 minute timestamp")
                    event = utc(datetime.fromisoformat(row["t"].replace("Z", "+00:00")))
                    candle = NativeCandle(
                        source="alpaca",
                        native_ticker=instrument.native_ticker,
                        feed="sip",
                        event_time=event,
                        ingestion_time=page.ingestion_time,
                        session_date=event.astimezone(NEW_YORK).date(),
                        page_index=index,
                        open=row["o"],
                        high=row["h"],
                        low=row["l"],
                        close=row["c"],
                        volume=row["v"],
                        trade_count=row["n"],
                        vwap=row.get("vw"),
                    )
                    if previous is not None and event <= previous:
                        raise NativeDataError("DUPLICATE_OR_UNORDERED_TIMESTAMP")
                    previous = event
                    if start <= event < end:
                        candles.append(candle)
                    else:
                        clipped += 1
            except (ValueError, TypeError, KeyError, ValidationError, OverflowError):
                raise NativeDataError("MALFORMED_BAR_PAYLOAD") from None
            if token is None:
                return NativeHistory(
                    instrument, start, end, tuple(pages), tuple(candles), "alpaca", clipped
                )
            if not rows or token in tokens:
                raise NativeDataError("PAGINATION_NO_PROGRESS")
            tokens.add(token)
            params["page_token"] = token
        raise NativeDataError("PAGINATION_PAGE_LIMIT")

    def replay_history(self, history: NativeHistory) -> NativeHistory:
        """Revalidate archived raw pages without authentication, network, or new ingestion times."""
        pages = iter(history.pages)

        def read_page(endpoint, params):
            page = next(pages, None)
            if page is None or page.endpoint != endpoint or page.params != params:
                raise NativeDataError("ARCHIVED_REQUEST_LINEAGE_MISMATCH")
            return page

        replayed = self._history(
            history.instrument, history.start, history.end, request_page=read_page
        )
        if replayed != history:
            raise NativeDataError("ARCHIVED_RAW_NORMALIZED_MISMATCH")
        return replayed

    def get_session_open(self, reality_symbol: str, session_date: date) -> NativeTarget:
        return session_target(self, self.calendar, reality_symbol, session_date, opening=True)

    def get_session_close(self, reality_symbol: str, session_date: date) -> NativeTarget:
        return session_target(self, self.calendar, reality_symbol, session_date, opening=False)


def native_provider(cohort: EvidenceQualifiedCohort) -> AlpacaNativeEquityProvider:
    if os.getenv("NATIVE_EQUITY_PROVIDER") != "alpaca":
        raise NativeDataError("NATIVE_PROVIDER_NOT_CONFIGURED", NativeCapability.GATED)
    return AlpacaNativeEquityProvider(cohort)
