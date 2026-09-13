import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sessionzero_bitget import BitgetMarketClient, BitgetReferenceDataProvider, export_history


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


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("SESSIONZERO_RUN_LIVE_TESTS") != "1",
    reason="set SESSIONZERO_RUN_LIVE_TESTS=1 to call Bitget",
)
def test_live_reality_history_export(tmp_path: Path) -> None:
    end = datetime.now(UTC) - timedelta(days=1)
    start = end - timedelta(days=7)
    output = tmp_path / "live-reality-history.jsonl"
    with BitgetMarketClient() as client:
        result = export_history(
            client,
            output_path=output,
            start=start,
            end=end,
            interval="1H",
            limit=2,
        )
    records = _read_export(output)
    assert result.record_count == len(records)
    assert records
    assert all(record["source"] == "bitget_uta_v3" for record in records)


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("SESSIONZERO_RUN_LIVE_TESTS") != "1",
    reason="set SESSIONZERO_RUN_LIVE_TESTS=1 to call Bitget",
)
def test_live_public_reference_mapping_and_actions() -> None:
    with BitgetMarketClient() as client:
        provider = BitgetReferenceDataProvider(client)
        mappings = {
            symbol: provider.get_mapping(symbol)[0].native_ticker
            for symbol in ("RAALUSDT", "RAAPLUSDT", "RMRNAUSDT")
        }
        dividends, dividend_splits, raw = provider.get_dividends_and_splits(mappings["RAAPLUSDT"])
    assert mappings == {"RAALUSDT": "AAL", "RAAPLUSDT": "AAPL", "RMRNAUSDT": "MRNA"}
    assert dividends or dividend_splits
    assert raw


def _read_export(path: Path) -> list[dict[str, object]]:
    import json

    return [json.loads(line) for line in path.read_text().splitlines()]
