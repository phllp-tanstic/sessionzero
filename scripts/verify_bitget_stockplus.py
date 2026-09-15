#!/usr/bin/env python3
"""Bounded, read-only verification of Bitget Stock+ market-data access.

Credentials are read only from the environment. The script never logs request
headers, signatures, credentials, or raw HTTP request objects, and it does not
write provider data to disk.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.bitget.com"
ENV_NAMES = ("BITGET_API_KEY", "BITGET_SECRET_KEY", "BITGET_PASSPHRASE")
SYMBOLS = ("AAPL.US", "NVDA.US", "TSLA.US")
PATH_STATIC = "/api/v3/stockplus/market/static"
PATH_CURRENT = "/api/v3/stockplus/market/candlestick"
PATH_HISTORY = "/api/v3/stockplus/market/history-candlestick"


def _credentials() -> tuple[str, str, str] | None:
    values = tuple(os.getenv(name, "") for name in ENV_NAMES)
    if not all(values):
        return None
    return values  # type: ignore[return-value]


def _signature(secret: str, timestamp: str, path: str, query: str) -> str:
    prehash = f"{timestamp}GET{path}?{query}"
    digest = hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _get(
    path: str, params: list[tuple[str, str]], credentials: tuple[str, str, str]
) -> dict[str, Any]:
    api_key, secret, passphrase = credentials
    query = urlencode(params)
    timestamp = str(time.time_ns() // 1_000_000)
    request = Request(
        f"{BASE_URL}{path}?{query}",
        headers={
            "ACCESS-KEY": api_key,
            "ACCESS-SIGN": _signature(secret, timestamp, path, query),
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        try:
            payload = json.loads(error.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"code": f"HTTP_{error.code}", "msg": "non-JSON provider error"}
    except URLError as error:
        return {"code": "NETWORK_ERROR", "msg": str(error.reason), "data": None}
    if not isinstance(payload, dict):
        return {"code": "SCHEMA_ERROR", "msg": "response envelope is not an object", "data": None}
    return payload


def _summary(
    endpoint: str, params: list[tuple[str, str]], payload: dict[str, Any]
) -> dict[str, Any]:
    data = payload.get("data")
    rows = data.get("list") if isinstance(data, dict) else None
    safe_params = {key: value for key, value in params}
    result: dict[str, Any] = {
        "endpoint": endpoint,
        "parameters": safe_params,
        "code": payload.get("code"),
        "message": payload.get("msg"),
        "requestTime": payload.get("requestTime"),
        "rowCount": len(rows) if isinstance(rows, list) else None,
    }
    if isinstance(rows, list) and rows:
        result["firstRow"] = rows[0]
        result["lastRow"] = rows[-1]
    return result


def _classify(payload: dict[str, Any]) -> str:
    if payload.get("code") == "00000":
        return "AVAILABLE"
    code = str(payload.get("code", ""))
    message = str(payload.get("msg", "")).lower()
    if code.startswith("4") and any(
        word in message
        for word in ("access", "permission", "auth", "eligible", "kyc", "market data")
    ):
        return "GATED"
    if code in {"NETWORK_ERROR", "SCHEMA_ERROR"}:
        return "DEGRADED"
    return "UNAVAILABLE"


def _epoch(value: str) -> str:
    return str(int(datetime.fromisoformat(value).timestamp()))


def main() -> int:
    credentials = _credentials()
    if credentials is None:
        print(
            json.dumps(
                {
                    "classification": "GATED",
                    "reason": "missing required environment credentials",
                    "requiredEnvironment": list(ENV_NAMES),
                    "requestsSent": 0,
                },
                indent=2,
            )
        )
        return 2

    results: list[dict[str, Any]] = []
    static_params = [("symbol", "AAPL.US")]
    static = _get(PATH_STATIC, static_params, credentials)
    results.append(_summary(PATH_STATIC, static_params, static))
    classification = _classify(static)
    if classification != "AVAILABLE":
        print(json.dumps({"classification": classification, "results": results}, indent=2))
        return 2

    # Current endpoint: small read proving its envelope and most recent hourly row.
    current_params = [
        ("symbol", "AAPL.US"),
        ("period", "Min_60"),
        ("count", "2"),
        ("adjustType", "NoAdjust"),
        ("tradeSessions", "Intraday"),
    ]
    current = _get(PATH_CURRENT, current_params, credentials)
    results.append(_summary(PATH_CURRENT, current_params, current))

    # Bounded recent history for the minimum requested native tickers.
    for symbol in SYMBOLS:
        params = [
            ("symbol", symbol),
            ("period", "Min_60"),
            ("count", "8"),
            ("adjustType", "NoAdjust"),
            ("tradeSessions", "Intraday"),
        ]
        payload = _get(PATH_HISTORY, params, credentials)
        results.append(_summary(PATH_HISTORY, params, payload))

    # Direction/time boundary behavior around two known XNYS regular sessions.
    for forward in ("false", "true"):
        params = [
            ("symbol", "AAPL.US"),
            ("period", "Min_60"),
            ("count", "12"),
            ("adjustType", "NoAdjust"),
            ("forward", forward),
            ("time", _epoch("2026-06-23T14:00:00+00:00")),
            ("tradeSessions", "Intraday"),
        ]
        payload = _get(PATH_HISTORY, params, credentials)
        results.append(_summary(PATH_HISTORY, params, payload))

    # Explicitly compare provider adjustment modes without choosing one.
    for adjustment in ("NoAdjust", "ForwardAdjust"):
        params = [
            ("symbol", "AAPL.US"),
            ("period", "Day"),
            ("count", "5"),
            ("adjustType", adjustment),
            ("forward", "false"),
            ("time", _epoch("2026-06-30T23:59:59+00:00")),
            ("tradeSessions", "Intraday"),
        ]
        payload = _get(PATH_HISTORY, params, credentials)
        results.append(_summary(PATH_HISTORY, params, payload))

    final_status = "AVAILABLE"
    if any(item["code"] != "00000" for item in results):
        final_status = "DEGRADED"
    print(
        json.dumps(
            {
                "classification": final_status,
                "verifiedAt": datetime.now(UTC).isoformat(),
                "readOnly": True,
                "requestsSent": len(results),
                "results": results,
            },
            indent=2,
        )
    )
    return 0 if final_status == "AVAILABLE" else 1


if __name__ == "__main__":
    sys.exit(main())
