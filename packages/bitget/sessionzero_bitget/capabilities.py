from __future__ import annotations

from datetime import UTC, datetime

from sessionzero_schemas import CapabilityStatus, ProviderCapability


def phase_zero_capabilities() -> list[ProviderCapability]:
    observed_at = datetime(2026, 9, 13, 15, 20, tzinfo=UTC)
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
        ProviderCapability(
            capability="reality_native_mapping",
            status=CapabilityStatus.AVAILABLE,
            reason="Officially documented public metadata; permanent identifiers are absent.",
            documented_endpoint="GET /api/v3/reality/market/stock-info",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="reality_dividends",
            status=CapabilityStatus.AVAILABLE,
            reason="Public endpoint is available; completeness is not established.",
            documented_endpoint="GET /api/v3/reality/market/dividends",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="reality_splits",
            status=CapabilityStatus.AVAILABLE,
            reason="Public Reality history and public split-record endpoints; coverage is partial.",
            documented_endpoint=(
                "GET /api/v3/reality/market/dividends; GET /api/v3/market/split-records"
            ),
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="reality_share_changes",
            status=CapabilityStatus.AVAILABLE,
            reason="Public point-in-time record; historical completeness is not established.",
            documented_endpoint="GET /api/v3/reality/market/share-capital-change",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="reality_suspensions",
            status=CapabilityStatus.AVAILABLE,
            reason="Public point-in-time record; historical completeness is not established.",
            documented_endpoint="GET /api/v3/reality/market/suspension-resumption-info",
            observed_at=observed_at,
        ),
        ProviderCapability(
            capability="reality_source_session_metadata",
            status=CapabilityStatus.AVAILABLE,
            reason="Public states and calendar metadata, retained as source semantics.",
            documented_endpoint=(
                "GET /api/v3/reality/market/states; GET /api/v3/reality/market/calendar"
            ),
            observed_at=observed_at,
        ),
    ]
