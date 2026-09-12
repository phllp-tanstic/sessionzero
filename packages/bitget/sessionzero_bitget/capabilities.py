from __future__ import annotations

from datetime import UTC, datetime

from sessionzero_schemas import CapabilityStatus, ProviderCapability


def phase_zero_capabilities() -> list[ProviderCapability]:
    observed_at = datetime(2026, 9, 12, 13, 50, tzinfo=UTC)
    return [
        ProviderCapability(
            capability="rtoken_instruments",
            status=CapabilityStatus.AVAILABLE,
            reason="Officially documented public and observed unauthenticated.",
            documented_endpoint="GET /api/v3/market/instruments",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="rtoken_tickers",
            status=CapabilityStatus.AVAILABLE,
            reason="Officially documented public and observed unauthenticated.",
            documented_endpoint="GET /api/v3/market/tickers",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="rtoken_candles",
            status=CapabilityStatus.AVAILABLE,
            reason="Officially documented and observed unauthenticated with Reality restrictions.",
            documented_endpoint="GET /api/v3/market/candles",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="rtoken_history_candles",
            status=CapabilityStatus.AVAILABLE,
            reason="Officially documented and observed unauthenticated.",
            documented_endpoint="GET /api/v3/market/history-candles",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="rtoken_depth",
            status=CapabilityStatus.GATED,
            reason=(
                "API key and Reality whitelist required; unauthenticated request returned 40006."
            ),
            documented_endpoint="GET /api/v3/account/reality-orderbook",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="rtoken_platform_fills",
            status=CapabilityStatus.GATED,
            reason=(
                "API key and Reality whitelist required; unauthenticated request returned 40006."
            ),
            documented_endpoint="GET /api/v3/account/reality-fills",
            observed_at=observed_at,
        ),
    ]
