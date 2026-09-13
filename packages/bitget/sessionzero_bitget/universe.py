from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sessionzero_market_data import CuratedBitgetSourceSessionProvider, SourceSessionProvider
from sessionzero_schemas import (
    RealityUniverseSnapshot,
    UniverseEligibilityReason,
    UniverseMappingStatus,
    UniverseMember,
)

from .client import REALITY_INTERVALS, BitgetMarketClient
from .errors import BitgetProviderError
from .reference import STOCK_INFO_ENDPOINT

UNIVERSE_SCHEMA_VERSION = "reality_universe.v1"
UNIVERSE_TRANSFORMATION_VERSION = "bitget_reality_universe.v1"
INSTRUMENTS_ENDPOINT = "/api/v3/market/instruments"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rows_by_symbol(data: Any, *, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError(f"{label} data must be an array")
    result: dict[str, dict[str, Any]] = {}
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("symbol"), str):
            raise ValueError(f"{label} row has malformed symbol metadata")
        symbol = row["symbol"]
        if symbol in result:
            raise ValueError(f"{label} contains duplicate symbol {symbol}")
        result[symbol] = row
    return result


def build_reality_universe_snapshot(
    client: BitgetMarketClient,
    *,
    interval: str = "1H",
    source_session_provider: SourceSessionProvider | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> RealityUniverseSnapshot:
    generated_at = clock().astimezone(UTC)
    session_provider = source_session_provider or CuratedBitgetSourceSessionProvider()
    discovery = client.get_instrument_discovery(category="SPOT")
    stock_info = client.request_public(STOCK_INFO_ENDPOINT)
    try:
        instrument_rows = _rows_by_symbol(discovery.payload.get("data"), label="instrument")
        stock_rows = _rows_by_symbol(stock_info.data, label="stock-info")
        reality = sorted(
            (item for item in discovery.instruments if item.is_reality),
            key=lambda item: item.symbol,
        )
        members: list[UniverseMember] = []
        for instrument in reality:
            raw_instrument = instrument_rows[instrument.symbol]
            stock = stock_rows.get(instrument.symbol)
            reasons: list[UniverseEligibilityReason] = []
            if instrument.status != "online":
                reasons.append(UniverseEligibilityReason.INSTRUMENT_NOT_ONLINE)
            if interval not in REALITY_INTERVALS:
                reasons.append(UniverseEligibilityReason.UNSUPPORTED_INTERVAL)
            native_ticker: str | None = None
            trading_periods: tuple[str, ...] = ()
            weekend_tradable: bool | None = None
            mapping_status = UniverseMappingStatus.UNAVAILABLE
            if stock is None:
                reasons.append(UniverseEligibilityReason.MISSING_NATIVE_MAPPING)
            else:
                code = stock.get("code")
                periods = stock.get("tradingPeriod")
                weekend = stock.get("weekendTradable")
                if (
                    not isinstance(code, str)
                    or not code
                    or not isinstance(periods, list)
                    or not all(isinstance(item, str) for item in periods)
                    or weekend not in {"yes", "no"}
                ):
                    raise ValueError(f"malformed stock-info metadata for {instrument.symbol}")
                native_ticker = code
                trading_periods = tuple(periods)
                weekend_tradable = weekend == "yes"
                mapping_status = UniverseMappingStatus.AVAILABLE
            session = session_provider.session_at(instrument.symbol, generated_at)
            raw_pair = {"instrument": raw_instrument, "stock_info": stock}
            members.append(
                UniverseMember(
                    reality_symbol=instrument.symbol,
                    base_coin=instrument.base_coin,
                    quote_coin=instrument.quote_coin,
                    native_ticker=native_ticker,
                    instrument_status=instrument.status,
                    is_reality=True,
                    launch_time=instrument.launch_time,
                    price_precision=instrument.price_precision,
                    quantity_precision=instrument.quantity_precision,
                    trading_periods=trading_periods,
                    weekend_tradable=weekend_tradable,
                    mapping_status=mapping_status,
                    source_session_status=session.availability.value,
                    source_session_mode=session.session_mode.value,
                    technically_eligible=not reasons,
                    exclusion_reasons=tuple(reasons),
                    raw_metadata_key=_hash(raw_pair),
                )
            )
        version_input = {
            "schema_version": UNIVERSE_SCHEMA_VERSION,
            "transformation_version": UNIVERSE_TRANSFORMATION_VERSION,
            "interval": interval,
            "members": [item.model_dump(mode="json") for item in members],
        }
        return RealityUniverseSnapshot(
            universe_version=_hash(version_input),
            schema_version=UNIVERSE_SCHEMA_VERSION,
            transformation_version=UNIVERSE_TRANSFORMATION_VERSION,
            generated_at=generated_at,
            source="bitget_uta_v3",
            source_endpoint=f"{INSTRUMENTS_ENDPOINT}+{STOCK_INFO_ENDPOINT}",
            source_version="uta_v3",
            interval=interval,
            members=tuple(members),
            raw_provider_payload={
                "instruments": discovery.payload,
                "stock_info": stock_info.payload,
            },
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise BitgetProviderError(
            kind="UPSTREAM_SCHEMA_ERROR",
            message="Bitget Reality universe metadata failed validation",
        ) from exc
