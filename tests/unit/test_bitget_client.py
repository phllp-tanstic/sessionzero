from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sessionzero_bitget.client import BitgetMarketClient
from sessionzero_bitget.errors import BitgetProviderError

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def response(payload: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def client_for(handler: object, retries: int = 0) -> BitgetMarketClient:
    return BitgetMarketClient(
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        max_retries=retries,
        clock=lambda: NOW,
    )


def fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text())


def test_instrument_parsing_reality_identification_and_filtering() -> None:
    with client_for(lambda _request: response(fixture("instruments.json"))) as client:
        instruments = client.get_reality_instruments()
    assert [item.symbol for item in instruments] == ["RTESTUSDT"]
    assert instruments[0].is_reality is True
    assert instruments[0].launch_time == datetime.fromtimestamp(1750000000, tz=UTC)
    assert instruments[0].ingestion_time == NOW


def test_ticker_normalization_and_utc_conversion() -> None:
    payload = {
        "code": "00000",
        "msg": "success",
        "requestTime": 1760000000000,
        "data": [
            {
                "symbol": "RTESTUSDT",
                "category": "SPOT",
                "ts": "1760000000000",
                "lastPrice": "10.25",
                "bid1Price": "10.24",
                "ask1Price": "10.26",
                "volume24h": "12.5",
                "turnover24h": "128.125",
                "platformTurnover24h": "4.5",
            }
        ],
    }
    with client_for(lambda _request: response(payload)) as client:
        ticker = client.get_ticker("RTESTUSDT")
    assert ticker.event_time.tzinfo is UTC
    assert str(ticker.last_price) == "10.25"
    assert str(ticker.platform_turnover_24h) == "4.5"


@pytest.mark.parametrize(
    ("row", "volume", "turnover"),
    [
        (["1760000000000", "10", "11", "9", "10.5", "", ""], None, None),
        (["1760000000000", "10", "11", "9", "10.5"], None, None),
        (["1760000000000", "10", "11", "9", "10.5", "0", "0"], "0", "0"),
    ],
)
def test_candle_missing_values_are_not_coerced_to_zero(
    row: list[str], volume: str | None, turnover: str | None
) -> None:
    payload = {"code": "00000", "msg": "success", "requestTime": 1, "data": [row]}
    with client_for(lambda _request: response(payload)) as client:
        candle = client.get_candles("RTESTUSDT", limit=1)[0]
    if volume is None:
        assert candle.volume is None
    else:
        assert str(candle.volume) == volume
    if turnover is None:
        assert candle.turnover is None
    else:
        assert str(candle.turnover) == turnover


def test_candles_are_sorted_and_marked_utc() -> None:
    rows = [
        ["1760003600000", "11", "12", "10", "11.5", "2", "23"],
        ["1760000000000", "10", "11", "9", "10.5", "1", "10.5"],
    ]
    payload = {"code": "00000", "msg": "success", "requestTime": 1, "data": rows}
    with client_for(lambda _request: response(payload)) as client:
        candles = client.get_candles("RTESTUSDT", limit=2)
    assert candles[0].event_time < candles[1].event_time
    assert all(item.event_time.tzinfo is UTC for item in candles)


def test_candle_observation_preserves_raw_provider_row() -> None:
    row = ["1760000000000", "10", "11", "9", "10.5", "", ""]
    payload = {"code": "00000", "msg": "success", "requestTime": 1, "data": [row]}
    with client_for(lambda _request: response(payload)) as client:
        observation = client.get_candle_observations("RTESTUSDT", historical=True, limit=1)[0]
    assert observation.payload == row
    assert observation.endpoint == "/api/v3/market/history-candles"
    assert observation.candle.close == Decimal("10.5")


def test_empty_candle_page_is_available_to_bounded_pagination() -> None:
    payload = {"code": "00000", "msg": "success", "requestTime": 1, "data": []}
    with client_for(lambda _request: response(payload)) as client:
        assert client.get_candle_observation_page("RTESTUSDT", historical=True) == []
    with (
        client_for(lambda _request: response(payload)) as client,
        pytest.raises(BitgetProviderError, match="no candles"),
    ):
        client.get_candles("RTESTUSDT", historical=True)


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        ({"unexpected": True}, "UPSTREAM_SCHEMA_ERROR"),
        (
            {"code": "00000", "msg": "success", "requestTime": 1, "data": {}},
            "UPSTREAM_SCHEMA_ERROR",
        ),
        (
            {"code": "00000", "msg": "success", "requestTime": 1, "data": []},
            "UPSTREAM_EMPTY_RESULT",
        ),
        (
            {"code": "40017", "msg": "bad parameter", "requestTime": 1, "data": None},
            "UPSTREAM_PROVIDER_ERROR",
        ),
    ],
)
def test_structured_upstream_failures(payload: object, kind: str) -> None:
    with (
        client_for(lambda _request: response(payload)) as client,
        pytest.raises(BitgetProviderError) as caught,
    ):
        client.get_instruments()
    assert caught.value.kind == kind


def test_malformed_instrument_row_is_rejected() -> None:
    payload = {
        "code": "00000",
        "msg": "success",
        "requestTime": 1,
        "data": [{"symbol": "BROKEN"}],
    }
    with (
        client_for(lambda _request: response(payload)) as client,
        pytest.raises(BitgetProviderError, match="failed validation"),
    ):
        client.get_instruments()


def test_network_timeout_is_structured_and_retryable() -> None:
    calls = 0

    def timeout(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out")

    with client_for(timeout, retries=1) as client, pytest.raises(BitgetProviderError) as caught:
        client.get_instruments()
    assert calls == 2
    assert caught.value.kind == "UPSTREAM_NETWORK_ERROR"
    assert caught.value.retryable is True


def test_http_error_is_structured() -> None:
    with (
        client_for(lambda _request: response({}, status=503)) as client,
        pytest.raises(BitgetProviderError) as caught,
    ):
        client.get_instruments()
    assert caught.value.kind == "UPSTREAM_HTTP_ERROR"
    assert caught.value.http_status == 503


def test_rate_limit_honors_retry_after_and_records_telemetry() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "1.5"}, json={})
        return response(fixture("instruments.json"))

    with BitgetMarketClient(
        transport=httpx.MockTransport(handler),
        max_retries=1,
        clock=lambda: NOW,
        sleeper=sleeps.append,
    ) as client:
        client.get_instruments()
        telemetry = client.request_telemetry
    assert calls == 2
    assert sleeps == [1.5]
    assert telemetry.request_count == 2
    assert telemetry.retry_count == 1
    assert telemetry.rate_limit_count == 1


def test_provider_rate_limit_retry_exhaustion_is_bounded() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response({"code": "429", "msg": "rate limited", "requestTime": 1, "data": None})

    with (
        BitgetMarketClient(
            transport=httpx.MockTransport(handler), max_retries=2, sleeper=lambda _delay: None
        ) as client,
        pytest.raises(BitgetProviderError) as caught,
    ):
        client.get_instruments()
    assert calls == 3
    assert caught.value.retryable is True
    assert client.request_telemetry.retry_count == 2
    assert client.request_telemetry.rate_limit_count == 3


def test_unsupported_reality_interval_is_rejected_before_network() -> None:
    with (
        client_for(lambda _request: pytest.fail("network should not be called")) as client,
        pytest.raises(ValueError, match="unsupported Reality interval"),
    ):
        client.get_candles("RTESTUSDT", interval="3m")
