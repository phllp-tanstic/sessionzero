from sessionzero_bitget.capabilities import phase_zero_capabilities
from sessionzero_schemas import CapabilityStatus


def test_capability_classification_is_evidence_based() -> None:
    capabilities = {item.capability: item.status for item in phase_zero_capabilities()}
    assert capabilities == {
        "rtoken_instruments": CapabilityStatus.AVAILABLE,
        "rtoken_tickers": CapabilityStatus.AVAILABLE,
        "rtoken_candles": CapabilityStatus.AVAILABLE,
        "rtoken_history_candles": CapabilityStatus.AVAILABLE,
        "rtoken_depth": CapabilityStatus.GATED,
        "rtoken_platform_fills": CapabilityStatus.GATED,
        "reality_native_mapping": CapabilityStatus.AVAILABLE,
        "reality_dividends": CapabilityStatus.AVAILABLE,
        "reality_splits": CapabilityStatus.AVAILABLE,
        "reality_share_changes": CapabilityStatus.AVAILABLE,
        "reality_suspensions": CapabilityStatus.AVAILABLE,
        "reality_source_session_metadata": CapabilityStatus.AVAILABLE,
    }
