from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from sessionzero_bitget import (
    BitgetMarketClient,
    BitgetProviderError,
    build_reality_universe_snapshot,
)
from sessionzero_market_data import (
    SourceAvailabilityState,
    SourceSessionAssessment,
    SourceSessionMode,
)
from sessionzero_schemas import UniverseEligibilityReason

NOW = datetime(2026, 9, 13, 15, 30, tzinfo=UTC)


class KnownSessions:
    def session_at(self, symbol: str, timestamp: datetime) -> SourceSessionAssessment:
        return SourceSessionAssessment(
            symbol=symbol,
            as_of=timestamp,
            availability=SourceAvailabilityState.EXPECTED_OPEN,
            session_mode=SourceSessionMode.TWENTY_FOUR_FIVE,
            reason="test evidence",
        )


def _handler(*, changed: bool = False, missing_mapping: bool = False):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/instruments"):
            data = [
                {
                    "symbol": "RBUSDT",
                    "baseCoin": "rB",
                    "quoteCoin": "USDT",
                    "category": "SPOT",
                    "status": "online",
                    "isReality": "yes",
                    "launchTime": "1780000000000",
                    "pricePrecision": "3" if changed else "2",
                    "quantityPrecision": "4",
                },
                {
                    "symbol": "RAUSDT",
                    "baseCoin": "rA",
                    "quoteCoin": "USDT",
                    "category": "SPOT",
                    "status": "offline",
                    "isReality": "yes",
                    "launchTime": None,
                    "pricePrecision": "2",
                    "quantityPrecision": "4",
                },
                {
                    "symbol": "BTCUSDT",
                    "baseCoin": "BTC",
                    "quoteCoin": "USDT",
                    "category": "SPOT",
                    "status": "online",
                    "isReality": "no",
                    "launchTime": None,
                    "pricePrecision": "2",
                    "quantityPrecision": "4",
                },
            ]
        else:
            data = [
                {
                    "symbol": "RAUSDT",
                    "code": "A",
                    "tradingPeriod": ["regular"],
                    "weekendTradable": "no",
                },
                *(
                    []
                    if missing_mapping
                    else [
                        {
                            "symbol": "RBUSDT",
                            "code": "B",
                            "tradingPeriod": ["regular"],
                            "weekendTradable": "yes",
                        }
                    ]
                ),
            ]
        return httpx.Response(
            200,
            json={"code": "00000", "msg": "success", "requestTime": 1789306347000, "data": data},
        )

    return handler


def _snapshot(*, changed: bool = False, missing_mapping: bool = False, at: datetime = NOW):
    with BitgetMarketClient(
        transport=httpx.MockTransport(_handler(changed=changed, missing_mapping=missing_mapping)),
        max_retries=0,
        clock=lambda: at,
    ) as client:
        return build_reality_universe_snapshot(
            client, source_session_provider=KnownSessions(), clock=lambda: at
        )


def test_universe_is_metadata_derived_sorted_versioned_and_auditable() -> None:
    first = _snapshot()
    later = _snapshot(at=datetime(2026, 9, 14, tzinfo=UTC))
    changed = _snapshot(changed=True)
    assert [item.reality_symbol for item in first.members] == ["RAUSDT", "RBUSDT"]
    assert first.universe_version == later.universe_version
    assert first.universe_version != changed.universe_version
    assert first.raw_provider_payload["instruments"]["data"][2]["symbol"] == "BTCUSDT"
    assert first.members[1].technically_eligible
    assert first.members[0].exclusion_reasons == (UniverseEligibilityReason.INSTRUMENT_NOT_ONLINE,)


def test_missing_mapping_and_unsupported_interval_are_explicit_exclusions() -> None:
    snapshot = _snapshot(missing_mapping=True)
    assert snapshot.members[1].exclusion_reasons == (
        UniverseEligibilityReason.MISSING_NATIVE_MAPPING,
    )
    unsupported = _snapshot()
    with BitgetMarketClient(transport=httpx.MockTransport(_handler()), max_retries=0) as client:
        unsupported = build_reality_universe_snapshot(
            client, interval="3m", source_session_provider=KnownSessions(), clock=lambda: NOW
        )
    assert all(
        UniverseEligibilityReason.UNSUPPORTED_INTERVAL in item.exclusion_reasons
        for item in unsupported.members
    )


def test_malformed_mapping_fails_closed_without_synthetic_fallback() -> None:
    def malformed(request: httpx.Request) -> httpx.Response:
        response = _handler()(request)
        if request.url.path.endswith("/stock-info"):
            payload = response.json()
            payload["data"][1]["code"] = ""
            return httpx.Response(200, json=payload)
        return response

    with (
        BitgetMarketClient(transport=httpx.MockTransport(malformed), max_retries=0) as client,
        pytest.raises(BitgetProviderError),
    ):
        build_reality_universe_snapshot(
            client, source_session_provider=KnownSessions(), clock=lambda: NOW
        )
