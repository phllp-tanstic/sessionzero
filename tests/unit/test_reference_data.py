from __future__ import annotations

import httpx
import pytest
from sessionzero_bitget import BitgetMarketClient, BitgetProviderError, BitgetReferenceDataProvider
from sessionzero_schemas import PointInTimeAvailability, ReferenceActionType

NOW_MS = 1789306347000


def _envelope(data: object, *, code: str = "00000") -> dict[str, object]:
    return {"code": code, "msg": "success", "requestTime": NOW_MS, "data": data}


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    cursor = request.url.params.get("cursor")
    if path.endswith("/instruments"):
        data = [{"symbol": "RAAPLUSDT", "baseCoin": "rAAPL", "isReality": "yes"}]
    elif path.endswith("/stock-info"):
        data = [
            {
                "symbol": "RAAPLUSDT",
                "code": "AAPL",
                "name": "Apple Inc.",
                "tradingPeriod": ["regular", "after_hours"],
                "weekendTradable": "no",
            }
        ]
    elif path.endswith("/dividends"):
        data = {
            "list": []
            if cursor
            else [
                {
                    "type": "cash_dividend",
                    "announcementDate": "1785427200000",
                    "recordDate": None,
                    "exrightDate": "2026-08-01",
                    "dividendDate": "2026-08-08",
                    "dividendPerShare": "0.25",
                    "stockDividendPerShare": None,
                },
                {
                    "type": "stock_split",
                    "announcementDate": None,
                    "recordDate": None,
                    "exrightDate": "2020-08-31",
                    "splitValidDate": "20200831",
                    "splitNumerator": "4",
                    "splitDenominator": "1",
                },
            ],
            "cursor": None,
        }
    elif path.endswith("/split-records"):
        data = [
            {
                "symbol": "MSTUUSDT",
                "type": "reverse_split",
                "status": "completed",
                "adjustmentRatio": "0.1",
                "exDividendDate": "20260901",
                "exDividendDateTimezone": "ET",
                "tradingHaltStartTime": None,
                "tradingHaltEndTime": None,
            }
        ]
    elif path.endswith("/share-capital-change"):
        data = {
            "announcementDate": "1785427200000",
            "changeDate": "1784217600000",
            "totalShares": "14594180000",
            "commonShares": "14594180000",
            "preferredShares": None,
            "otherShares": None,
            "specialExplain": None,
            "changeReason": "change",
        }
    elif path.endswith("/suspension-resumption-info"):
        data = {
            "code": "AAPL",
            "name": "Apple Inc.",
            "suspensionDate": "1546358400000",
            "suspensionTime": "16:25:05",
            "suspensionReason": "news",
            "suspensionPrice": None,
            "resumptionDate": "1546358400000",
            "resumptionQuoteTime": "16:45",
            "resumptionTradingTime": "16:50",
        }
    elif path.endswith("/states"):
        data = {
            "market": "US",
            "daylightType": "standard",
            "stateList": [
                {"state": "regular", "timeZone": "EST", "startTime": "09:30", "endTime": "16:00"}
            ],
        }
    elif path.endswith("/calendar"):
        data = {
            "timeZone": "EST",
            "specificConfig": [
                {
                    "remark": "holiday",
                    "startTime": "2026-12-25 00:00",
                    "endTime": "2026-12-26 00:00",
                }
            ],
            "regularConfig": ["SATURDAY", "SUNDAY"],
        }
    else:
        raise AssertionError(path)
    return httpx.Response(200, json=_envelope(data))


def _provider(handler=_handler) -> BitgetReferenceDataProvider:
    client = BitgetMarketClient(transport=httpx.MockTransport(handler), max_retries=0)
    return BitgetReferenceDataProvider(client, minimum_reality_request_interval=0)


def test_reference_bundle_parses_typed_records_and_retains_raw_payloads() -> None:
    bundle = _provider().get_reference_bundle("RAAPLUSDT")
    assert (
        bundle.mapping.reality_symbol,
        bundle.mapping.base_coin,
        bundle.mapping.native_ticker,
    ) == ("RAAPLUSDT", "rAAPL", "AAPL")
    assert bundle.mapping.permanent_identifier is None
    assert bundle.mapping.availability_time_status == PointInTimeAvailability.UNKNOWN
    assert bundle.dividends[0].action_type == ReferenceActionType.CASH_DIVIDEND
    assert str(bundle.dividends[0].cash_amount_per_share) == "0.25"
    assert {item.action_type for item in bundle.splits} == {
        ReferenceActionType.SPLIT,
        ReferenceActionType.REVERSE_SPLIT,
    }
    assert bundle.share_changes[0].preferred_shares is None
    assert bundle.suspensions[0].suspension_price is None
    assert bundle.source_session_metadata.market == "US"
    assert len(bundle.raw_responses) == 8
    assert all(raw.payload["code"] == "00000" for raw in bundle.raw_responses)


def test_empty_actions_are_valid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(
            ("/dividends", "/share-capital-change", "/suspension-resumption-info")
        ):
            data: object = (
                {"list": [], "cursor": None} if request.url.path.endswith("/dividends") else None
            )
            return httpx.Response(200, json=_envelope(data))
        return _handler(request)

    provider = _provider(handler)
    assert provider.get_dividends_and_splits("AAPL")[:2] == ((), ())
    assert provider.get_share_changes("AAPL")[0] == ()
    assert provider.get_suspensions("AAPL")[0] == ()


@pytest.mark.parametrize("field,value", [("code", ""), ("symbol", "RMSFTUSDT")])
def test_mapping_fails_closed_without_string_slicing(field: str, value: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stock-info"):
            row = {
                "symbol": "RAAPLUSDT",
                "code": "AAPL",
                "tradingPeriod": ["regular"],
                "weekendTradable": "no",
            }
            row[field] = value
            return httpx.Response(200, json=_envelope([row]))
        return _handler(request)

    with pytest.raises(BitgetProviderError) as caught:
        _provider(handler).get_mapping("RAAPLUSDT")
    assert caught.value.kind == "UPSTREAM_SCHEMA_ERROR"


def test_invalid_ratio_status_date_and_provider_error_fail_closed() -> None:
    for field, value in (
        ("adjustmentRatio", "bad"),
        ("status", "mystery"),
        ("exDividendDate", "bad"),
    ):

        def handler(request: httpx.Request, field=field, value=value) -> httpx.Response:
            if request.url.path.endswith("/split-records"):
                row = {
                    "symbol": "X",
                    "type": "split",
                    "status": "pending",
                    "adjustmentRatio": "2",
                    "exDividendDate": "20260101",
                    "exDividendDateTimezone": "ET",
                    "tradingHaltStartTime": None,
                    "tradingHaltEndTime": None,
                }
                row[field] = value
                return httpx.Response(200, json=_envelope([row]))
            return _handler(request)

        with pytest.raises(BitgetProviderError):
            _provider(handler).get_split_records()

    def rejected(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope(None, code="40001"))

    with pytest.raises(BitgetProviderError) as caught:
        _provider(rejected).get_mapping("RAAPLUSDT")
    assert caught.value.kind == "UPSTREAM_PROVIDER_ERROR"
