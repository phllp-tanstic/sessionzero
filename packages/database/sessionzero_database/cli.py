from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

from sessionzero_bitget import BitgetMarketClient, BitgetProviderError
from sessionzero_config import get_settings
from sqlalchemy.exc import SQLAlchemyError

from .engine import create_database_engine, verify_database_connection
from .persistence import ingest_candle_observations


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include an offset")
    return parsed.astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Persist one real Bitget Reality historical candle window to PostgreSQL"
    )
    parser.add_argument("--start", required=True, type=_parse_utc)
    parser.add_argument("--end", required=True, type=_parse_utc)
    parser.add_argument("--symbol")
    parser.add_argument("--interval", default="1H")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.start >= args.end or args.end - args.start > timedelta(days=90):
        parser.error("range must be increasing and no longer than 90 days")

    settings = get_settings()
    engine = None
    try:
        database_url = settings.require_database_url()
        engine = create_database_engine(database_url)
        verify_database_connection(engine)
        with BitgetMarketClient(
            base_url=str(settings.bitget_base_url),
            timeout_seconds=settings.bitget_timeout_seconds,
            max_retries=settings.bitget_max_retries,
        ) as client:
            instruments = sorted(
                (item for item in client.get_reality_instruments() if item.status == "online"),
                key=lambda item: item.symbol,
            )
            if not instruments:
                raise ValueError("no online Reality instrument is available")
            symbol = args.symbol.upper() if args.symbol else instruments[0].symbol
            if symbol not in {item.symbol for item in instruments}:
                raise ValueError(
                    "symbol is not an online Reality instrument discovered from Bitget"
                )
            observations = client.get_candle_observations(
                symbol,
                interval=args.interval,
                limit=args.limit,
                historical=True,
                start_time_ms=int(args.start.timestamp() * 1000),
                end_time_ms=int(args.end.timestamp() * 1000),
            )
        observations = [
            item for item in observations if args.start <= item.candle.event_time < args.end
        ]
        if not observations:
            raise ValueError("Bitget returned no observations inside the requested range")
        result = ingest_candle_observations(engine, observations)
    except (BitgetProviderError, SQLAlchemyError, ValueError) as exc:
        print(json.dumps({"error": {"code": "INGESTION_FAILED", "message": str(exc)}}))
        raise SystemExit(1) from exc
    finally:
        if engine is not None:
            engine.dispose()

    print(
        json.dumps(
            {
                "run_id": str(result.run_id),
                "symbol": symbol,
                "interval": args.interval,
                "requested_start": args.start.isoformat(),
                "requested_end": args.end.isoformat(),
                "records_received": result.records_received,
                "raw_records_written": result.raw_records_written,
                "normalized_records_written": result.normalized_records_written,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
