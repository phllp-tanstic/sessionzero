import os

import pytest
from sessionzero_bitget import BitgetMarketClient


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("SESSIONZERO_RUN_LIVE_TESTS") != "1",
    reason="set SESSIONZERO_RUN_LIVE_TESTS=1 to call Bitget",
)
def test_live_reality_market_surface() -> None:
    with BitgetMarketClient() as client:
        instruments = client.get_reality_instruments()
        symbol = sorted(item.symbol for item in instruments if item.status == "online")[0]
        assert client.get_ticker(symbol).symbol == symbol
        assert client.get_candles(symbol, limit=2)
        assert client.get_candles(symbol, limit=2, historical=True)
