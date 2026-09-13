from __future__ import annotations

import hashlib
import json
import time as time_module
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError
from sessionzero_schemas import (
    DividendRecord,
    MarketClosure,
    MarketSessionWindow,
    RealitySymbolMapping,
    ReferenceActionType,
    ShareCapitalChange,
    SourceSessionMetadata,
    SplitRecord,
    SuspensionRecord,
)

from .client import BitgetMarketClient, PublicResponse
from .errors import BitgetProviderError

STOCK_INFO_ENDPOINT = "/api/v3/reality/market/stock-info"
DIVIDENDS_ENDPOINT = "/api/v3/reality/market/dividends"
SPLIT_RECORDS_ENDPOINT = "/api/v3/market/split-records"
SHARE_CAPITAL_ENDPOINT = "/api/v3/reality/market/share-capital-change"
SUSPENSIONS_ENDPOINT = "/api/v3/reality/market/suspension-resumption-info"
MARKET_STATES_ENDPOINT = "/api/v3/reality/market/states"
MARKET_CALENDAR_ENDPOINT = "/api/v3/reality/market/calendar"
INSTRUMENTS_ENDPOINT = "/api/v3/market/instruments"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class RawReferenceResponse:
    endpoint: str
    params: dict[str, str]
    payload: dict[str, Any]
    provider_request_time: datetime
    ingestion_time: datetime
    provider_record_key: str


@dataclass(frozen=True, slots=True)
class ReferenceDataBundle:
    mapping: RealitySymbolMapping
    dividends: tuple[DividendRecord, ...]
    splits: tuple[SplitRecord, ...]
    share_changes: tuple[ShareCapitalChange, ...]
    suspensions: tuple[SuspensionRecord, ...]
    source_session_metadata: SourceSessionMetadata
    raw_responses: tuple[RawReferenceResponse, ...]

    @property
    def normalized_record_count(self) -> int:
        return (
            2
            + len(self.dividends)
            + len(self.splits)
            + len(self.share_changes)
            + len(self.suspensions)
        )


def _record_key(record_type: str, value: object) -> str:
    canonical = json.dumps(
        {"record_type": record_type, "value": value},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("optional text field must be text or null")
    return value


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid decimal value: {value!r}") from exc


def _provider_date(value: Any, field: str) -> date | None:
    if value is None or value == "":
        return None
    if not isinstance(value, (str, int)):
        raise ValueError(f"{field} must be a date string or epoch milliseconds")
    text = str(value)
    try:
        if text.isdigit() and len(text) >= 11:
            return datetime.fromtimestamp(int(text) / 1000, tz=UTC).date()
        if text.isdigit() and len(text) == 8:
            return datetime.strptime(text, "%Y%m%d").date()
        return date.fromisoformat(text)
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def _provider_time(value: Any, field: str) -> time | None:
    if value is None or value == "":
        return None
    try:
        return time.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def _milliseconds_to_utc(value: Any, field: str) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (OSError, OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


class BitgetReferenceDataProvider:
    """Public Bitget Reality reference metadata, distinct from price and calendar providers."""

    def __init__(
        self,
        client: BitgetMarketClient,
        *,
        clock: Callable[[], datetime] = _utc_now,
        minimum_reality_request_interval: float = 1.05,
        sleeper: Callable[[float], None] = time_module.sleep,
        monotonic: Callable[[], float] = time_module.monotonic,
    ) -> None:
        self._client = client
        self._clock = clock
        self._minimum_interval = minimum_reality_request_interval
        self._sleeper = sleeper
        self._monotonic = monotonic
        self._last_reality_request: float | None = None

    def _request(
        self, path: str, params: dict[str, str] | None = None
    ) -> tuple[PublicResponse, RawReferenceResponse]:
        request_params = params or {}
        if path.startswith("/api/v3/reality/") and self._last_reality_request is not None:
            remaining = self._minimum_interval - (self._monotonic() - self._last_reality_request)
            if remaining > 0:
                self._sleeper(remaining)
        response = self._client.request_public(path, request_params)
        if path.startswith("/api/v3/reality/"):
            self._last_reality_request = self._monotonic()
        ingested_at = self._clock()
        raw = RawReferenceResponse(
            endpoint=path,
            params=dict(request_params),
            payload=response.payload,
            provider_request_time=response.request_time,
            ingestion_time=ingested_at,
            provider_record_key=_record_key(
                "raw_response",
                {"endpoint": path, "params": request_params, "payload": response.payload},
            ),
        )
        return response, raw

    def get_mapping(
        self, reality_symbol: str
    ) -> tuple[RealitySymbolMapping, tuple[RawReferenceResponse, ...]]:
        symbol = reality_symbol.upper()
        instrument_response, instrument_raw = self._request(
            INSTRUMENTS_ENDPOINT, {"category": "SPOT", "symbol": symbol}
        )
        stock_response, stock_raw = self._request(STOCK_INFO_ENDPOINT, {"symbol": symbol})
        try:
            if not isinstance(instrument_response.data, list) or len(instrument_response.data) != 1:
                raise ValueError("instrument lookup did not return exactly one record")
            if not isinstance(stock_response.data, list) or len(stock_response.data) != 1:
                raise ValueError("stock-info lookup did not return exactly one record")
            instrument = instrument_response.data[0]
            stock = stock_response.data[0]
            if not isinstance(instrument, dict) or not isinstance(stock, dict):
                raise ValueError("mapping inputs must be objects")
            if instrument.get("symbol") != symbol or stock.get("symbol") != symbol:
                raise ValueError("provider returned a contradictory symbol")
            if instrument.get("isReality") != "yes":
                raise ValueError("instrument is not identified as Reality metadata")
            periods = stock.get("tradingPeriod")
            if not isinstance(periods, list) or not all(isinstance(item, str) for item in periods):
                raise ValueError("tradingPeriod must be a list of session names")
            weekend_value = stock.get("weekendTradable")
            if weekend_value not in {"yes", "no"}:
                raise ValueError("invalid weekendTradable value")
            mapping_source = {"instrument": instrument, "stock_info": stock}
            mapping = RealitySymbolMapping(
                endpoint=STOCK_INFO_ENDPOINT,
                provider_record_key=_record_key("reality_mapping", mapping_source),
                ingestion_time=stock_raw.ingestion_time,
                reality_symbol=_required_text(stock.get("symbol"), "symbol"),
                base_coin=_required_text(instrument.get("baseCoin"), "baseCoin"),
                native_ticker=_required_text(stock.get("code"), "code"),
                name=_optional_text(stock.get("name")),
                trading_periods=tuple(periods),
                weekend_tradable=weekend_value == "yes",
                effective_time=None,
                permanent_identifier=None,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget Reality mapping failed validation",
            ) from exc
        return mapping, (instrument_raw, stock_raw)

    def get_dividends_and_splits(
        self, native_ticker: str, *, max_pages: int = 20
    ) -> tuple[
        tuple[DividendRecord, ...], tuple[SplitRecord, ...], tuple[RawReferenceResponse, ...]
    ]:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        ticker = native_ticker.upper()
        cursor: str | None = None
        seen_cursors: set[str] = set()
        dividends: list[DividendRecord] = []
        splits: list[SplitRecord] = []
        raw_responses: list[RawReferenceResponse] = []
        try:
            for _ in range(max_pages):
                params = {"code": ticker, "limit": "100"}
                if cursor is not None:
                    params["cursor"] = cursor
                response, raw = self._request(DIVIDENDS_ENDPOINT, params)
                raw_responses.append(raw)
                if not isinstance(response.data, dict):
                    raise ValueError("dividend data must be an object")
                rows = response.data.get("list")
                if rows is None and response.data.get("cursor") is None:
                    rows = []
                if not isinstance(rows, list):
                    raise ValueError("dividend list must be an array")
                for row in rows:
                    if not isinstance(row, dict):
                        raise ValueError("dividend row must be an object")
                    action_type = row.get("type")
                    key = _record_key("dividend_history", {"code": ticker, "row": row})
                    common = {
                        "endpoint": DIVIDENDS_ENDPOINT,
                        "provider_record_key": key,
                        "ingestion_time": raw.ingestion_time,
                    }
                    if action_type in {"cash_dividend", "stock_dividend"}:
                        dividends.append(
                            DividendRecord(
                                **common,
                                native_ticker=ticker,
                                action_type=(
                                    ReferenceActionType.CASH_DIVIDEND
                                    if action_type == "cash_dividend"
                                    else ReferenceActionType.STOCK_DIVIDEND
                                ),
                                announcement_date=_provider_date(
                                    row.get("announcementDate"), "announcementDate"
                                ),
                                record_date=_provider_date(row.get("recordDate"), "recordDate"),
                                ex_date=_provider_date(row.get("exrightDate"), "exrightDate"),
                                payment_date=_provider_date(
                                    row.get("dividendDate"), "dividendDate"
                                ),
                                effective_date=_provider_date(
                                    row.get("exrightDate"), "exrightDate"
                                ),
                                cash_amount_per_share=_optional_decimal(
                                    row.get("dividendPerShare")
                                ),
                                stock_amount_per_share=_optional_decimal(
                                    row.get("stockDividendPerShare")
                                ),
                                currency=None,
                            )
                        )
                    elif action_type == "stock_split":
                        effective_date = _provider_date(row.get("splitValidDate"), "splitValidDate")
                        if effective_date is None:
                            raise ValueError("stock split is missing splitValidDate")
                        splits.append(
                            SplitRecord(
                                **common,
                                native_ticker=ticker,
                                action_type=ReferenceActionType.SPLIT,
                                announcement_date=_provider_date(
                                    row.get("announcementDate"), "announcementDate"
                                ),
                                record_date=_provider_date(row.get("recordDate"), "recordDate"),
                                ex_date=_provider_date(row.get("exrightDate"), "exrightDate"),
                                effective_date=effective_date,
                                numerator=_optional_decimal(row.get("splitNumerator")),
                                denominator=_optional_decimal(row.get("splitDenominator")),
                            )
                        )
                    else:
                        raise ValueError(f"unsupported dividend action type: {action_type!r}")
                next_cursor = response.data.get("cursor")
                if next_cursor in {None, ""} or not rows:
                    break
                if not isinstance(next_cursor, str) or next_cursor in seen_cursors:
                    raise ValueError("invalid or non-progressing dividend cursor")
                seen_cursors.add(next_cursor)
                cursor = next_cursor
            else:
                raise ValueError("dividend pagination exceeded max_pages")
        except (InvalidOperation, TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget dividend history failed validation",
            ) from exc
        return tuple(dividends), tuple(splits), tuple(raw_responses)

    def get_split_records(self) -> tuple[tuple[SplitRecord, ...], tuple[RawReferenceResponse, ...]]:
        response, raw = self._request(SPLIT_RECORDS_ENDPOINT)
        try:
            if not isinstance(response.data, list):
                raise ValueError("split records must be an array")
            records: list[SplitRecord] = []
            for row in response.data:
                if not isinstance(row, dict):
                    raise ValueError("split row must be an object")
                action = row.get("type")
                if action not in {"split", "reverse_split"}:
                    raise ValueError("invalid split type")
                status = row.get("status")
                if status not in {"pending", "ongoing", "completed"}:
                    raise ValueError("invalid split status")
                effective_date = _provider_date(row.get("exDividendDate"), "exDividendDate")
                if effective_date is None:
                    raise ValueError("split record is missing exDividendDate")
                records.append(
                    SplitRecord(
                        endpoint=SPLIT_RECORDS_ENDPOINT,
                        provider_record_key=_record_key("split_record", row),
                        ingestion_time=raw.ingestion_time,
                        provider_symbol=_required_text(row.get("symbol"), "symbol"),
                        action_type=(
                            ReferenceActionType.SPLIT
                            if action == "split"
                            else ReferenceActionType.REVERSE_SPLIT
                        ),
                        effective_date=effective_date,
                        adjustment_ratio=_optional_decimal(row.get("adjustmentRatio")),
                        provider_status=status,
                        event_timezone=_required_text(
                            row.get("exDividendDateTimezone"), "exDividendDateTimezone"
                        ),
                        trading_halt_start=_milliseconds_to_utc(
                            row.get("tradingHaltStartTime"), "tradingHaltStartTime"
                        ),
                        trading_halt_end=_milliseconds_to_utc(
                            row.get("tradingHaltEndTime"), "tradingHaltEndTime"
                        ),
                    )
                )
        except (TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR", message="Bitget split records failed validation"
            ) from exc
        return tuple(records), (raw,)

    def get_share_changes(
        self, native_ticker: str
    ) -> tuple[tuple[ShareCapitalChange, ...], tuple[RawReferenceResponse, ...]]:
        ticker = native_ticker.upper()
        response, raw = self._request(SHARE_CAPITAL_ENDPOINT, {"code": ticker})
        try:
            if response.data is None or response.data == "" or response.data == {}:
                return (), (raw,)
            if not isinstance(response.data, dict):
                raise ValueError("share-capital data must be an object or null")
            row = response.data
            effective_date = _provider_date(row.get("changeDate"), "changeDate")
            if effective_date is None:
                raise ValueError("share-capital change is missing changeDate")
            record = ShareCapitalChange(
                endpoint=SHARE_CAPITAL_ENDPOINT,
                provider_record_key=_record_key(
                    "share_capital_change", {"code": ticker, "row": row}
                ),
                ingestion_time=raw.ingestion_time,
                native_ticker=ticker,
                announcement_date=_provider_date(row.get("announcementDate"), "announcementDate"),
                effective_date=effective_date,
                total_shares=_optional_decimal(row.get("totalShares")),
                common_shares=_optional_decimal(row.get("commonShares")),
                preferred_shares=_optional_decimal(row.get("preferredShares")),
                other_shares=_optional_decimal(row.get("otherShares")),
                special_explanation=_optional_text(row.get("specialExplain")),
                change_reason=_optional_text(row.get("changeReason")),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget share-capital data failed validation",
            ) from exc
        return (record,), (raw,)

    def get_suspensions(
        self, native_ticker: str
    ) -> tuple[tuple[SuspensionRecord, ...], tuple[RawReferenceResponse, ...]]:
        ticker = native_ticker.upper()
        response, raw = self._request(SUSPENSIONS_ENDPOINT, {"code": ticker})
        try:
            if response.data is None or response.data == "" or response.data == {}:
                return (), (raw,)
            if not isinstance(response.data, dict):
                raise ValueError("suspension data must be an object or null")
            row = response.data
            returned_ticker = _required_text(row.get("code"), "code")
            if returned_ticker != ticker:
                raise ValueError("provider returned a contradictory native ticker")
            suspension_date = _provider_date(row.get("suspensionDate"), "suspensionDate")
            if suspension_date is None:
                raise ValueError("suspension record is missing suspensionDate")
            record = SuspensionRecord(
                endpoint=SUSPENSIONS_ENDPOINT,
                provider_record_key=_record_key("suspension", {"code": ticker, "row": row}),
                ingestion_time=raw.ingestion_time,
                native_ticker=ticker,
                name=_optional_text(row.get("name")),
                suspension_date=suspension_date,
                suspension_time=_provider_time(row.get("suspensionTime"), "suspensionTime"),
                suspension_reason=_optional_text(row.get("suspensionReason")),
                suspension_price=_optional_decimal(row.get("suspensionPrice")),
                resumption_date=_provider_date(row.get("resumptionDate"), "resumptionDate"),
                resumption_quote_time=_provider_time(
                    row.get("resumptionQuoteTime"), "resumptionQuoteTime"
                ),
                resumption_trading_time=_provider_time(
                    row.get("resumptionTradingTime"), "resumptionTradingTime"
                ),
                event_timezone=None,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget suspension data failed validation",
            ) from exc
        return (record,), (raw,)

    def get_source_session_metadata(
        self,
    ) -> tuple[SourceSessionMetadata, tuple[RawReferenceResponse, ...]]:
        states_response, states_raw = self._request(MARKET_STATES_ENDPOINT)
        calendar_response, calendar_raw = self._request(MARKET_CALENDAR_ENDPOINT)
        try:
            states_data = states_response.data
            if isinstance(states_data, list):
                if len(states_data) != 1:
                    raise ValueError("market states did not contain exactly one US market")
                states_data = states_data[0]
            if not isinstance(states_data, dict) or not isinstance(calendar_response.data, dict):
                raise ValueError("session metadata must be objects")
            state_rows = states_data.get("stateList")
            if not isinstance(state_rows, list) or not state_rows:
                raise ValueError("stateList must be a non-empty array")
            sessions = tuple(
                MarketSessionWindow(
                    state=_required_text(row.get("state"), "state"),
                    time_zone=_required_text(row.get("timeZone"), "timeZone"),
                    start_time=_provider_time(row.get("startTime"), "startTime"),
                    end_time=_provider_time(row.get("endTime"), "endTime"),
                )
                for row in state_rows
                if isinstance(row, dict)
            )
            if len(sessions) != len(state_rows):
                raise ValueError("market state row must be an object")
            state_time_zones = {item.time_zone for item in sessions}
            if len(state_time_zones) != 1:
                raise ValueError("market sessions contain contradictory timezones")
            calendar = calendar_response.data
            closure_rows = calendar.get("specificConfig")
            closure_days = calendar.get("regularConfig")
            if not isinstance(closure_rows, list) or not isinstance(closure_days, list):
                raise ValueError("calendar closure fields must be arrays")
            closures = tuple(
                MarketClosure(
                    remark=_optional_text(row.get("remark")),
                    start_local=datetime.strptime(
                        _required_text(row.get("startTime"), "startTime"), "%Y-%m-%d %H:%M"
                    ),
                    end_local=datetime.strptime(
                        _required_text(row.get("endTime"), "endTime"), "%Y-%m-%d %H:%M"
                    ),
                )
                for row in closure_rows
                if isinstance(row, dict)
            )
            if len(closures) != len(closure_rows) or not all(
                isinstance(item, str) for item in closure_days
            ):
                raise ValueError("invalid calendar row")
            combined = {"states": states_data, "calendar": calendar}
            metadata = SourceSessionMetadata(
                endpoint=f"{MARKET_STATES_ENDPOINT}+{MARKET_CALENDAR_ENDPOINT}",
                provider_record_key=_record_key("source_session_metadata", combined),
                ingestion_time=calendar_raw.ingestion_time,
                market=_required_text(states_data.get("market"), "market"),
                daylight_type=_required_text(states_data.get("daylightType"), "daylightType"),
                state_time_zone=next(iter(state_time_zones)),
                calendar_time_zone=_required_text(calendar.get("timeZone"), "timeZone"),
                sessions=sessions,
                closures=closures,
                regular_closure_days=tuple(closure_days),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise BitgetProviderError(
                kind="UPSTREAM_SCHEMA_ERROR",
                message="Bitget source-session metadata failed validation",
            ) from exc
        return metadata, (states_raw, calendar_raw)

    def get_reference_bundle(self, reality_symbol: str) -> ReferenceDataBundle:
        mapping, mapping_raw = self.get_mapping(reality_symbol)
        dividends, dividend_splits, dividends_raw = self.get_dividends_and_splits(
            mapping.native_ticker
        )
        public_splits, splits_raw = self.get_split_records()
        share_changes, share_raw = self.get_share_changes(mapping.native_ticker)
        suspensions, suspension_raw = self.get_suspensions(mapping.native_ticker)
        session_metadata, session_raw = self.get_source_session_metadata()
        return ReferenceDataBundle(
            mapping=mapping,
            dividends=dividends,
            splits=dividend_splits + public_splits,
            share_changes=share_changes,
            suspensions=suspensions,
            source_session_metadata=session_metadata,
            raw_responses=(
                mapping_raw + dividends_raw + splits_raw + share_raw + suspension_raw + session_raw
            ),
        )
