from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sessionzero_config import get_settings
from sessionzero_schemas import MarketCandle, MarketInstrument

from .client import BitgetMarketClient
from .errors import BitgetProviderError

MAX_HISTORY_RANGE = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class ExportResult:
    output_path: Path
    symbol: str
    interval: str
    requested_start: datetime
    requested_end: datetime
    record_count: int
    oldest_event_time: datetime
    newest_event_time: datetime
    missing_volume: int
    missing_turnover: int
    file_size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_path": str(self.output_path),
            "symbol": self.symbol,
            "interval": self.interval,
            "requested_start": self.requested_start.isoformat(),
            "requested_end": self.requested_end.isoformat(),
            "record_count": self.record_count,
            "oldest_event_time": self.oldest_event_time.isoformat(),
            "newest_event_time": self.newest_event_time.isoformat(),
            "missing_volume": self.missing_volume,
            "missing_turnover": self.missing_turnover,
            "file_size_bytes": self.file_size_bytes,
        }


class HistoryExportError(ValueError):
    """Raised when an export request cannot produce a complete valid artifact."""


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryExportError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HistoryExportError("timestamps must include an explicit UTC offset")
    return parsed.astimezone(UTC)


def _validate_range(start: datetime, end: datetime) -> None:
    if (
        start.tzinfo is None
        or start.utcoffset() is None
        or end.tzinfo is None
        or end.utcoffset() is None
    ):
        raise HistoryExportError("requested range must use timezone-aware timestamps")
    if start >= end:
        raise HistoryExportError("start must be earlier than end")
    if end - start > MAX_HISTORY_RANGE:
        raise HistoryExportError("Bitget historical candle ranges cannot exceed 90 days")


def _select_instrument(
    instruments: list[MarketInstrument], requested_symbol: str | None
) -> MarketInstrument:
    online = sorted(
        (instrument for instrument in instruments if instrument.status == "online"),
        key=lambda instrument: instrument.symbol,
    )
    if not online:
        raise HistoryExportError("no online Reality instrument is available")
    if requested_symbol is None:
        return online[0]
    normalized = requested_symbol.upper()
    try:
        return next(instrument for instrument in online if instrument.symbol.upper() == normalized)
    except StopIteration as exc:
        raise HistoryExportError(
            f"symbol is not an online Reality instrument discovered from Bitget: {requested_symbol}"
        ) from exc


def _canonical_line(candle: MarketCandle) -> str:
    return json.dumps(
        candle.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _publish_jsonl(path: Path, candles: list[MarketCandle], *, overwrite: bool) -> int:
    if path.exists() and not overwrite:
        raise HistoryExportError(f"output already exists; pass --overwrite to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            for candle in candles:
                temporary.write(_canonical_line(candle))
                temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return path.stat().st_size


def export_history(
    client: BitgetMarketClient,
    *,
    output_path: Path,
    start: datetime,
    end: datetime,
    interval: str,
    limit: int = 100,
    symbol: str | None = None,
    overwrite: bool = False,
) -> ExportResult:
    _validate_range(start, end)
    start = start.astimezone(UTC)
    end = end.astimezone(UTC)

    selected = _select_instrument(client.get_reality_instruments(), symbol)
    candles = client.get_candles(
        selected.symbol,
        interval=interval,
        limit=limit,
        historical=True,
        start_time_ms=int(start.timestamp() * 1000),
        end_time_ms=int(end.timestamp() * 1000),
    )
    candles = sorted(
        (candle for candle in candles if start <= candle.event_time < end),
        key=lambda candle: candle.event_time,
    )
    if not candles:
        raise HistoryExportError("Bitget returned no candles inside the requested range")
    event_times = [candle.event_time for candle in candles]
    if len(event_times) != len(set(event_times)):
        raise HistoryExportError("Bitget returned duplicate candle event times")

    file_size = _publish_jsonl(output_path, candles, overwrite=overwrite)
    return ExportResult(
        output_path=output_path,
        symbol=selected.symbol,
        interval=interval,
        requested_start=start,
        requested_end=end,
        record_count=len(candles),
        oldest_event_time=candles[0].event_time,
        newest_event_time=candles[-1].event_time,
        missing_volume=sum(candle.volume is None for candle in candles),
        missing_turnover=sum(candle.turnover is None for candle in candles),
        file_size_bytes=file_size,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export normalized Bitget Reality historical candles as canonical JSONL"
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start", required=True, type=_parse_utc)
    parser.add_argument("--end", required=True, type=_parse_utc)
    parser.add_argument("--interval", default="1H")
    parser.add_argument("--limit", default=100, type=int)
    parser.add_argument("--symbol", help="Must be present in live Reality metadata")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    try:
        with BitgetMarketClient(
            base_url=str(settings.bitget_base_url),
            timeout_seconds=settings.bitget_timeout_seconds,
            max_retries=settings.bitget_max_retries,
        ) as client:
            result = export_history(
                client,
                output_path=args.output,
                start=args.start,
                end=args.end,
                interval=args.interval,
                limit=args.limit,
                symbol=args.symbol,
                overwrite=args.overwrite,
            )
    except (BitgetProviderError, HistoryExportError, ValueError, OSError) as exc:
        error = (
            exc.as_dict()
            if isinstance(exc, BitgetProviderError)
            else {"error": {"code": "EXPORT_FAILED", "message": str(exc)}}
        )
        print(json.dumps(error, sort_keys=True))
        raise SystemExit(1) from exc

    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
