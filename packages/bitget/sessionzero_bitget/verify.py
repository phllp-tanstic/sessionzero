from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sessionzero_config import get_settings

from .capabilities import phase_zero_capabilities
from .client import BitgetMarketClient
from .errors import BitgetProviderError


def _as_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_as_json(item) for item in value]
    return value


def verify(*, interval: str, limit: int) -> dict[str, Any]:
    settings = get_settings()
    with BitgetMarketClient(
        base_url=str(settings.bitget_base_url),
        timeout_seconds=settings.bitget_timeout_seconds,
        max_retries=settings.bitget_max_retries,
    ) as client:
        instruments = sorted(client.get_reality_instruments(), key=lambda item: item.symbol)
        selected = next((item for item in instruments if item.status == "online"), instruments[0])
        ticker = client.get_ticker(selected.symbol)
        current = client.get_candles(selected.symbol, interval=interval, limit=limit)
        history_end = datetime.now(UTC) - timedelta(days=91)
        history_start = history_end - timedelta(days=30)
        history = client.get_candles(
            selected.symbol,
            interval=interval,
            limit=limit,
            historical=True,
            start_time_ms=int(history_start.timestamp() * 1000),
            end_time_ms=int(history_end.timestamp() * 1000),
        )

    return {
        "verification_time": datetime.now(UTC).isoformat(),
        "authenticated": False,
        "reality_instrument_count": len(instruments),
        "selected_instrument": _as_json(selected),
        "ticker": _as_json(ticker),
        "current_candles": {
            "interval": interval,
            "count": len(current),
            "oldest": current[0].event_time.isoformat(),
            "newest": current[-1].event_time.isoformat(),
            "missing_volume": sum(item.volume is None for item in current),
            "missing_turnover": sum(item.turnover is None for item in current),
        },
        "historical_candles": {
            "interval": interval,
            "count": len(history),
            "oldest": history[0].event_time.isoformat(),
            "newest": history[-1].event_time.isoformat(),
            "missing_volume": sum(item.volume is None for item in history),
            "missing_turnover": sum(item.turnover is None for item in history),
        },
        "capabilities": _as_json(phase_zero_capabilities()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify public Bitget Reality market data")
    parser.add_argument("--interval", default="1H")
    parser.add_argument("--limit", default=5, type=int)
    args = parser.parse_args()
    try:
        result = verify(interval=args.interval, limit=args.limit)
    except (BitgetProviderError, ValueError) as exc:
        error = (
            exc.as_dict()
            if isinstance(exc, BitgetProviderError)
            else {"error": {"code": "INVALID_ARGUMENT", "message": str(exc)}}
        )
        print(json.dumps(error, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
