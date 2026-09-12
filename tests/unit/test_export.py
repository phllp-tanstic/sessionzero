from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import sessionzero_bitget.export as export_module
from sessionzero_bitget import BitgetMarketClient, BitgetProviderError
from sessionzero_bitget.export import export_history

START = datetime(2026, 6, 10, tzinfo=UTC)
END = datetime(2026, 6, 11, tzinfo=UTC)
INGESTED_AT = datetime(2026, 9, 12, 14, 0, tzinfo=UTC)


def _instrument_envelope() -> dict[str, object]:
    return {
        "code": "00000",
        "msg": "success",
        "requestTime": 1781000000000,
        "data": [
            {
                "symbol": "RTESTUSDT",
                "category": "SPOT",
                "baseCoin": "rTEST",
                "quoteCoin": "USDT",
                "status": "online",
                "isReality": "yes",
                "launchTime": "1780000000000",
                "pricePrecision": "2",
                "quantityPrecision": "4",
            },
            {
                "symbol": "BTCUSDT",
                "category": "SPOT",
                "baseCoin": "BTC",
                "quoteCoin": "USDT",
                "status": "online",
                "isReality": "no",
                "launchTime": "1532454360000",
                "pricePrecision": "2",
                "quantityPrecision": "6",
            },
        ],
    }


def _candle_envelope(rows: list[object]) -> dict[str, object]:
    return {
        "code": "00000",
        "msg": "success",
        "requestTime": 1781000000000,
        "data": rows,
    }


def _client(rows: list[object], ingestion_time: datetime = INGESTED_AT) -> BitgetMarketClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v3/market/instruments":
            return httpx.Response(200, json=_instrument_envelope())
        if request.url.path == "/api/v3/market/history-candles":
            return httpx.Response(200, json=_candle_envelope(rows))
        raise AssertionError(f"unexpected path: {request.url.path}")

    return BitgetMarketClient(
        transport=httpx.MockTransport(handler),
        max_retries=0,
        clock=lambda: ingestion_time,
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_normalized_history_exports_in_deterministic_order_with_utc_and_nulls(
    tmp_path: Path,
) -> None:
    rows = [
        ["1781053200000", "11", "12", "10", "11.5", "2", "23"],
        ["1781049600000", "10", "11", "9", "10.5", "", ""],
    ]
    output = tmp_path / "history.jsonl"

    with _client(rows) as client:
        result = export_history(
            client,
            output_path=output,
            start=START,
            end=END,
            interval="1H",
            symbol="rtestusdt",
        )

    records = _read_jsonl(output)
    assert result.record_count == 2
    assert [record["event_time"] for record in records] == [
        "2026-06-10T00:00:00Z",
        "2026-06-10T01:00:00Z",
    ]
    assert records[0]["source"] == "bitget_uta_v3"
    assert records[0]["symbol"] == "RTESTUSDT"
    assert records[0]["market"] == "SPOT"
    assert records[0]["raw_or_derived"] == "RAW"
    assert records[0]["interval"] == "1H"
    assert records[0]["ingestion_time"] == "2026-09-12T14:00:00Z"
    assert records[0]["volume"] is None
    assert records[0]["turnover"] is None
    assert records[1]["volume"] == "2"
    assert records[1]["turnover"] == "23"
    assert output.read_bytes().endswith(b"\n")


def test_same_observations_have_deterministic_content_except_ingestion_time(
    tmp_path: Path,
) -> None:
    rows = [["1781049600000", "10", "11", "9", "10.5", "1", "10.5"]]
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    later = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)

    with _client(rows) as client:
        export_history(
            client,
            output_path=first,
            start=START,
            end=END,
            interval="1H",
        )
    with _client(rows, later) as client:
        export_history(
            client,
            output_path=second,
            start=START,
            end=END,
            interval="1H",
        )

    first_record = _read_jsonl(first)[0]
    second_record = _read_jsonl(second)[0]
    assert first_record.pop("ingestion_time") != second_record.pop("ingestion_time")
    assert first_record == second_record


def test_fixed_ingestion_time_produces_byte_identical_jsonl(tmp_path: Path) -> None:
    rows = [["1781049600000", "10", "11", "9", "10.5", "1", "10.5"]]
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    for output in (first, second):
        with _client(rows) as client:
            export_history(
                client,
                output_path=output,
                start=START,
                end=END,
                interval="1H",
            )
    assert first.read_bytes() == second.read_bytes()


def test_malformed_upstream_data_prevents_artifact(tmp_path: Path) -> None:
    output = tmp_path / "must-not-exist.jsonl"
    malformed_rows = [["not-a-timestamp", "10", "11", "9", "10.5"]]
    with _client(malformed_rows) as client, pytest.raises(BitgetProviderError):
        export_history(
            client,
            output_path=output,
            start=START,
            end=END,
            interval="1H",
        )
    assert not output.exists()


def test_provider_failure_does_not_replace_existing_artifact(tmp_path: Path) -> None:
    output = tmp_path / "existing.jsonl"
    output.write_text("existing artifact\n")

    def failure(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": "40017", "msg": "failure", "requestTime": 1, "data": None},
        )

    with (
        BitgetMarketClient(
            transport=httpx.MockTransport(failure), max_retries=0, clock=lambda: INGESTED_AT
        ) as client,
        pytest.raises(BitgetProviderError),
    ):
        export_history(
            client,
            output_path=output,
            start=START,
            end=END,
            interval="1H",
            overwrite=True,
        )
    assert output.read_text() == "existing artifact\n"


def test_production_exporter_has_no_fixture_input_path() -> None:
    source = inspect.getsource(export_module)
    assert "tests/fixtures" not in source
    assert "--fixture" not in source
    assert "--input" not in source
