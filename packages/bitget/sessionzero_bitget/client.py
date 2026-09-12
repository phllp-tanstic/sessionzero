from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError
from sessionzero_schemas import MarketCandle, MarketInstrument, MarketTicker

from .errors import BitgetProviderError

REALITY_INTERVALS = frozenset({"1m", "5m", "15m", "1H", "4H", "1D"})
HISTORY_CANDLES_ENDPOINT = "/api/v3/market/history-candles"
CURRENT_CANDLES_ENDPOINT = "/api/v3/market/candles"


@dataclass(frozen=True, slots=True)
class CandleObservation:
    candle: MarketCandle
    payload: list[Any]
    endpoint: str


class _Envelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    msg: str
    requestTime: int
    data: Any


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _milliseconds_to_utc(value: str | int) -> datetime:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError) as exc:
        raise ValueError(f"invalid millisecond timestamp: {value!r}") from exc


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid decimal value: {value!r}") from exc


class BitgetMarketClient:
    def __init__(
        self,
        *,
        base_url: str = "https://api.bitget.com",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "SessionZero/0.1"},
        )
        self._max_retries = max_retries
        self._clock = clock

    def __enter__(self) -> BitgetMarketClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, path: str, params: dict[str, str]) -> _Envelope:
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(path, params=params)
                if (
                    response.status_code == 429 or response.status_code >= 500
                ) and attempt < self._max_retries:
                    time.sleep(0.2 * (2**attempt))
                    continue
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < self._max_retries:
                    time.sleep(0.2 * (2**attempt))
                    continue
                raise BitgetProviderError(
                    kind="UPSTREAM_NETWORK_ERROR",
                    message="Bitget market data request failed",
                    retryable=True,
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise BitgetProviderError(
                    kind="UPSTREAM_HTTP_ERROR",
                    message="Bitget returned an HTTP error",
                    http_status=exc.response.status_code,
                    retryable=exc.response.status_code == 429 or exc.response.status_code >= 500,
                ) from exc

            try:
                payload = response.json()
                envelope = _Envelope.model_validate(payload)
            except (ValueError, ValidationError) as exc:
                raise BitgetProviderError(
                    kind="UPSTREAM_SCHEMA_ERROR",
                    message="Bitget returned a malformed response",
                ) from exc

            if envelope.code != "00000":
                raise BitgetProviderError(
                    kind="UPSTREAM_PROVIDER_ERROR",
                    message="Bitget rejected the market data request",
                    provider_code=envelope.code,
                    retryable=envelope.code in {"429", "40762"},
                )
            return envelope
        raise AssertionError("request retry loop exited unexpectedly")

    def get_instruments(self, *, category: str = "SPOT") -> list[MarketInstrument]:
        envelope = self._request("/api/v3/market/instruments", {"category": category})
        if not isinstance(envelope.data, list):
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget instrument data is not a list",
            )
        if not envelope.data:
            raise BitgetProviderError(
                kind="UPSTREAM_EMPTY_RESULT",
                message="Bitget returned no instruments",
            )
        ingested_at = self._clock()
        try:
            return [self._normalize_instrument(item, ingested_at) for item in envelope.data]
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget instrument data failed validation",
            ) from exc

    def get_reality_instruments(self) -> list[MarketInstrument]:
        instruments = [item for item in self.get_instruments() if item.is_reality]
        if not instruments:
            raise BitgetProviderError(
                kind="UPSTREAM_EMPTY_RESULT",
                message="Bitget returned no Reality instruments",
            )
        return instruments

    def get_ticker(self, symbol: str) -> MarketTicker:
        envelope = self._request("/api/v3/market/tickers", {"category": "SPOT", "symbol": symbol})
        if not isinstance(envelope.data, list) or len(envelope.data) != 1:
            raise BitgetProviderError(
                kind="UPSTREAM_EMPTY_RESULT",
                message="Bitget returned no unique ticker for the symbol",
            )
        item = envelope.data[0]
        try:
            return MarketTicker(
                symbol=item["symbol"],
                market=item["category"],
                event_time=_milliseconds_to_utc(item["ts"]),
                ingestion_time=self._clock(),
                last_price=Decimal(item["lastPrice"]),
                bid_price=_optional_decimal(item.get("bid1Price")),
                ask_price=_optional_decimal(item.get("ask1Price")),
                volume_24h=_optional_decimal(item.get("volume24h")),
                turnover_24h=_optional_decimal(item.get("turnover24h")),
                platform_turnover_24h=_optional_decimal(item.get("platformTurnover24h")),
            )
        except (KeyError, TypeError, ValueError, InvalidOperation, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget ticker data failed validation",
            ) from exc

    def get_candles(
        self,
        symbol: str,
        *,
        interval: str = "1H",
        limit: int = 100,
        historical: bool = False,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[MarketCandle]:
        return [
            observation.candle
            for observation in self.get_candle_observations(
                symbol,
                interval=interval,
                limit=limit,
                historical=historical,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )
        ]

    def get_candle_observations(
        self,
        symbol: str,
        *,
        interval: str = "1H",
        limit: int = 100,
        historical: bool = False,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[CandleObservation]:
        observations = self.get_candle_observation_page(
            symbol,
            interval=interval,
            limit=limit,
            historical=historical,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
        if not observations:
            raise BitgetProviderError(
                kind="UPSTREAM_EMPTY_RESULT", message="Bitget returned no candles"
            )
        return sorted(observations, key=lambda item: item.candle.event_time)

    def get_candle_observation_page(
        self,
        symbol: str,
        *,
        interval: str = "1H",
        limit: int = 100,
        historical: bool = False,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[CandleObservation]:
        if interval not in REALITY_INTERVALS:
            raise ValueError(f"unsupported Reality interval: {interval}")
        maximum = 100 if historical else 1000
        if not 1 <= limit <= maximum:
            raise ValueError(f"limit must be between 1 and {maximum}")
        params = {
            "category": "SPOT",
            "symbol": symbol,
            "interval": interval,
            "type": "market",
            "limit": str(limit),
        }
        if start_time_ms is not None:
            params["startTime"] = str(start_time_ms)
        if end_time_ms is not None:
            params["endTime"] = str(end_time_ms)
        path = HISTORY_CANDLES_ENDPOINT if historical else CURRENT_CANDLES_ENDPOINT
        envelope = self._request(path, params)
        if not isinstance(envelope.data, list):
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR", message="Bitget candle data is not a list"
            )
        if not envelope.data:
            return []
        ingested_at = self._clock()
        try:
            observations = [
                CandleObservation(
                    candle=self._normalize_candle(row, symbol, interval, ingested_at),
                    payload=list(row),
                    endpoint=path,
                )
                for row in envelope.data
            ]
        except (IndexError, TypeError, ValueError, InvalidOperation, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget candle data failed validation",
            ) from exc
        return observations

    @staticmethod
    def _normalize_instrument(item: Any, ingested_at: datetime) -> MarketInstrument:
        if not isinstance(item, dict):
            raise TypeError("instrument row must be an object")
        is_reality = item["isReality"] == "yes"
        if item["isReality"] not in {"yes", "no"}:
            raise ValueError("unknown isReality value")
        launch = item.get("launchTime")
        return MarketInstrument(
            symbol=item["symbol"],
            base_coin=item["baseCoin"],
            quote_coin=item["quoteCoin"],
            market=item["category"],
            status=item["status"],
            is_reality=is_reality,
            launch_time=_milliseconds_to_utc(launch) if launch not in {None, ""} else None,
            price_precision=int(item["pricePrecision"])
            if item.get("pricePrecision") not in {None, ""}
            else None,
            quantity_precision=int(item["quantityPrecision"])
            if item.get("quantityPrecision") not in {None, ""}
            else None,
            ingestion_time=ingested_at,
        )

    @staticmethod
    def _normalize_candle(
        row: Any, symbol: str, interval: str, ingested_at: datetime
    ) -> MarketCandle:
        if not isinstance(row, list) or len(row) < 5:
            raise ValueError("candle row must contain at least OHLC and time")
        return MarketCandle(
            symbol=symbol,
            market="SPOT",
            event_time=_milliseconds_to_utc(row[0]),
            ingestion_time=ingested_at,
            interval=interval,
            open=Decimal(str(row[1])),
            high=Decimal(str(row[2])),
            low=Decimal(str(row[3])),
            close=Decimal(str(row[4])),
            volume=_optional_decimal(row[5] if len(row) > 5 else None),
            turnover=_optional_decimal(row[6] if len(row) > 6 else None),
        )
