"""Synthetic contract fixtures only; these prices are never runtime evidence."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sessionzero_market_data.alpaca import AlpacaNativeEquityProvider, native_provider
from sessionzero_market_data.calendar import XnysTradingCalendar
from sessionzero_market_data.native import NativeCapability, NativeDataError
from sessionzero_schemas import EvidenceQualifiedCohort, EvidenceQualifiedCohortMember

START = datetime(2026, 6, 16, 13, 30, tzinfo=UTC)
NOW = datetime(2026, 9, 19, tzinfo=UTC)


@pytest.fixture
def native_cohort():
    return EvidenceQualifiedCohort(
        cohort_version="a" * 64,
        universe_version="b" * 64,
        derivation_version="test",
        source_session_evidence_version="test",
        interval="1H",
        evaluation_start=datetime(2026, 6, 15, 20, tzinfo=UTC),
        evaluation_end=datetime(2026, 9, 13, 20, tzinfo=UTC),
        members=(
            EvidenceQualifiedCohortMember(
                symbol="EXPLICIT_MAPPING",
                native_ticker="AAPL",
                source_session_evidence_ids=("test",),
            ),
        ),
    )


def bar(t=START, **values):
    return {
        "t": t.isoformat() if isinstance(t, datetime) else t,
        "o": "100.00000000000000000000000000001",
        "h": "102",
        "l": "99",
        "c": "101",
        "v": 10,
        "n": 2,
        "vw": "100.5",
        **values,
    }


def payload(rows, token=None):
    return {"symbol": "AAPL", "bars": rows, "next_page_token": token}


@pytest.fixture
def make_provider(native_cohort, monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "test-only-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-only-secret")
    clients = []

    def make(handler, **kwargs):
        client = AlpacaNativeEquityProvider(
            native_cohort,
            transport=httpx.MockTransport(handler),
            clock=lambda: NOW,
            sleep=lambda _: None,
            **kwargs,
        )
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


def test_auth_explicit_contract_pagination_clipping_and_mapping(make_provider, caplog):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["APCA-API-KEY-ID"] == "test-only-key"
        assert request.headers["APCA-API-SECRET-KEY"] == "test-only-secret"
        assert request.url.path == "/v2/stocks/AAPL/bars"
        assert (
            dict(request.url.params).items()
            >= {
                "feed": "sip",
                "adjustment": "raw",
                "timeframe": "1Min",
                "asof": "-",
                "sort": "asc",
            }.items()
        )
        rows = [bar()] if len(requests) == 1 else [bar(START + timedelta(minutes=1))]
        return httpx.Response(
            200,
            json=payload(rows, "page2" if len(requests) == 1 else None),
            headers={
                "X-Request-ID": "test-request",
                "X-RateLimit-Limit": "200",
                "Authorization": "do-not-retain",
            },
        )

    provider = make_provider(handler, page_limit=1)
    history = provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))
    assert len(history.pages) == 2 and len(history.candles) == 1 and history.clipped_count == 1
    assert requests[1].url.params["page_token"] == "page2"
    assert history.candles[0].open == Decimal("100.00000000000000000000000000001")
    assert history.candles[0].event_time.tzinfo == UTC
    assert history.pages[0].response_headers == {
        "x-request-id": "test-request",
        "x-ratelimit-limit": "200",
    }
    assert provider.health() == NativeCapability.AVAILABLE
    assert "test-only-secret" not in caplog.text
    with pytest.raises(NativeDataError, match="ACCEPTED_MAPPING_REQUIRED"):
        provider.get_instrument("RAAPLUSDT")


def test_missing_credentials_and_configuration_fail_closed(make_provider, monkeypatch):
    provider = make_provider(lambda _: pytest.fail("must not send"))
    monkeypatch.delenv("ALPACA_SECRET_KEY")
    assert provider.health() == NativeCapability.GATED
    with pytest.raises(NativeDataError, match="MISSING_ALPACA_CREDENTIALS"):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))
    monkeypatch.delenv("NATIVE_EQUITY_PROVIDER", raising=False)
    with pytest.raises(NativeDataError, match="NOT_CONFIGURED"):
        native_provider(None)


@pytest.mark.parametrize("status", [401, 403, 400, 422, 302])
def test_provider_failure_no_fallback(make_provider, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="unsafe-provider-text")

    provider = make_provider(handler)
    with pytest.raises(NativeDataError) as exc:
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))
    assert "unsafe-provider-text" not in str(exc.value)
    assert len(calls) == 1


def test_retry_after_and_rate_limit_exhaustion(make_provider):
    calls, delays = [], []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "2", "X-Request-ID": "throttled"})

    provider = make_provider(handler, max_retries=2)
    provider.sleep = delays.append
    with pytest.raises(NativeDataError, match="HTTP_RETRIES_EXHAUSTED"):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))
    assert provider.telemetry == {"requests": 3, "retries": 2, "rate_limits": 3}
    assert delays.count(2) == 2
    assert provider.health() == NativeCapability.DEGRADED
    assert provider.attempts[0]["headers"]["x-request-id"] == "throttled"


@pytest.mark.parametrize(
    "headers, expected",
    [
        ({"Retry-After": "Sat, 19 Sep 2026 00:00:03 GMT"}, 3),
        ({"X-RateLimit-Reset": str(int(NOW.timestamp()) + 4)}, 4),
    ],
)
def test_retry_header_forms(make_provider, headers, expected):
    provider = make_provider(lambda _: None)
    assert provider._delay(httpx.Response(429, headers=headers), 0) == expected


def test_excessive_retry_after_stops(make_provider):
    provider = make_provider(lambda _: httpx.Response(429, headers={"Retry-After": "120"}))
    with pytest.raises(NativeDataError, match="DELAY_EXCEEDS_BUDGET"):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))
    assert provider.telemetry["requests"] == 1


@pytest.mark.parametrize("rows", [[], None])
def test_empty_history_is_valid_missing_target(make_provider, rows):
    provider = make_provider(lambda _: httpx.Response(200, json=payload(rows)))
    target = provider.get_session_open("EXPLICIT_MAPPING", START.date())
    assert target.price is None and target.status == "MISSING_BOUNDARY_MINUTE"
    assert target.history.candles == () and len(target.history.pages) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"symbol": "OTHER", "bars": [], "next_page_token": None},
        payload([bar(h="90")]),
        payload([bar(v=-1)]),
        payload([bar(n=1.5)]),
        payload([bar(t="2026-06-16T13:30:00")]),
        payload([bar(t="invalid")]),
        payload([bar(t="2026-06-16T13:30:01Z")]),
        payload([bar(o="NaN")]),
        payload([bar(), bar()]),
        payload([bar(START + timedelta(minutes=1)), bar()]),
        payload([], 123),
    ],
)
def test_malformed_and_duplicate_history(make_provider, bad):
    provider = make_provider(lambda _: httpx.Response(200, json=bad))
    with pytest.raises(NativeDataError):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=2))


@pytest.mark.parametrize("mode", ["empty", "repeated_token", "duplicate", "page_limit"])
def test_pagination_guards(make_provider, mode):
    calls = []

    def handler(request):
        calls.append(request)
        t = START if mode == "duplicate" else START + timedelta(minutes=len(calls) - 1)
        token = "same" if mode == "repeated_token" else str(len(calls))
        return httpx.Response(200, json=payload([] if mode == "empty" else [bar(t)], token))

    provider = make_provider(handler, max_pages=3)
    with pytest.raises(NativeDataError):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=5))
    assert len(calls) <= 3


@pytest.mark.parametrize(
    "session_day, open_hour, close_hour",
    [
        (date(2026, 3, 6), 14, 21),
        (date(2026, 3, 9), 13, 20),
        (date(2026, 11, 27), 14, 18),
    ],
)
def test_exact_xnys_boundary_targets(make_provider, session_day, open_hour, close_hour):
    session = XnysTradingCalendar().session_on(session_day)

    def handler(request):
        start = datetime.fromisoformat(request.url.params["start"])
        return httpx.Response(200, json=payload([bar(start), bar(start + timedelta(minutes=1))]))

    provider = make_provider(handler)
    provider.clock = lambda: datetime(2027, 1, 1, tzinfo=UTC)
    opening = provider.get_session_open("EXPLICIT_MAPPING", session_day)
    closing = provider.get_session_close("EXPLICIT_MAPPING", session_day)
    assert opening.regular_open.hour == open_hour and closing.regular_close.hour == close_hour
    assert opening.candle.event_time == session.regular_open
    assert closing.candle.event_time == session.regular_close - timedelta(minutes=1)
    assert opening.definition == "FIRST_1M_BAR_OPEN" and closing.definition == "LAST_1M_BAR_CLOSE"
    assert opening.price == Decimal(bar()["o"]) and closing.price == Decimal("101")


@pytest.mark.parametrize("opening", [True, False])
def test_adjacent_minute_never_replaces_missing_boundary(make_provider, opening):
    def handler(request):
        start = datetime.fromisoformat(request.url.params["start"])
        return httpx.Response(
            200,
            json=payload([bar(start - timedelta(minutes=1)), bar(start + timedelta(minutes=1))]),
        )

    provider = make_provider(handler)
    target = (provider.get_session_open if opening else provider.get_session_close)(
        "EXPLICIT_MAPPING", START.date()
    )
    assert target.price is None and target.history.clipped_count == 2


def test_holiday_and_embargo(make_provider):
    provider = make_provider(lambda _: pytest.fail("must not request"))
    with pytest.raises(ValueError, match="not an XNYS"):
        provider.get_session_open("EXPLICIT_MAPPING", date(2026, 6, 19))
    with pytest.raises(NativeDataError, match="EMBARGO"):
        provider.get_candles("EXPLICIT_MAPPING", NOW - timedelta(hours=1), NOW)
    with pytest.raises(ValueError, match="timezone"):
        provider.get_candles("EXPLICIT_MAPPING", datetime(2026, 6, 16), NOW)


def test_transient_network_and_server_retry(make_provider):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("private request details")
        if len(calls) == 2:
            return httpx.Response(503)
        return httpx.Response(200, json=payload([bar()]))

    provider = make_provider(handler)
    assert (
        len(provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1)).candles)
        == 1
    )
    assert provider.telemetry["retries"] == 2


@pytest.mark.parametrize(
    "body",
    [
        '{"symbol":"AAPL","bars":[],"bars":[],"next_page_token":null}',
        '{"symbol":"AAPL","bars":[],"next_page_token":NaN}',
    ],
)
def test_invalid_json_does_not_normalize_silently(make_provider, body):
    provider = make_provider(lambda _: httpx.Response(200, text=body))
    with pytest.raises(NativeDataError, match="MALFORMED"):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))


def test_sub_microsecond_timestamp_is_not_truncated(make_provider):
    provider = make_provider(
        lambda _: httpx.Response(200, json=payload([bar(t="2026-06-16T13:30:00.000000001Z")]))
    )
    with pytest.raises(NativeDataError, match="MALFORMED"):
        provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))


def test_bounded_probe_selection_and_raw_evidence(native_cohort, monkeypatch):
    from sessionzero_database.native_cli import probe

    monkeypatch.setenv("ALPACA_API_KEY", "test-only-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-only-secret")
    cohort = native_cohort.model_copy(
        update={
            "members": tuple(
                EvidenceQualifiedCohortMember(
                    symbol=f"TEST_{i}", native_ticker=ticker, source_session_evidence_ids=("test",)
                )
                for i, ticker in enumerate(("AAPL", "NVDA", "TSLA", "TESTA", "TESTB"))
            )
        }
    )

    def handler(request):
        start = datetime.fromisoformat(request.url.params["start"])
        end = datetime.fromisoformat(request.url.params["end"])
        offset = int(request.url.params.get("page_token", "0"))
        limit = int(request.url.params["limit"])
        times = [
            start + timedelta(minutes=i) for i in range(int((end - start).total_seconds() / 60) + 1)
        ]
        rows = [bar(t) for t in times[offset : offset + limit]]
        next_offset = offset + limit
        token = str(next_offset) if next_offset < len(times) else None
        return httpx.Response(
            200,
            json={
                "symbol": request.url.path.split("/")[-2],
                "bars": rows,
                "next_page_token": token,
            },
            headers={"x-request-id": "test-id"},
        )

    provider = AlpacaNativeEquityProvider(
        cohort, transport=httpx.MockTransport(handler), clock=lambda: NOW, sleep=lambda _: None
    )
    try:
        report = probe(provider, cohort)
        assert report["accepted"]
        assert len(report["pilot"]) == 3 and len(report["availability"]) == 5
        assert len(report["target_pairs"]) == 25
        assert len({row["cash_session_date"] for row in report["target_pairs"]}) == 5
        assert all(
            row["next_opening"]["session_date"] > row["cash_session_date"]
            for row in report["target_pairs"]
        )
        assert all(h["pages"] for h in report["histories"])
        assert all(
            p["response_headers"]["x-request-id"] == "test-id"
            for h in report["histories"]
            for p in h["pages"]
        )
        assert report["public_raw_display"] == "NOT_APPROVED"
    finally:
        provider.close()


def test_post_normalization_boundary_leakage_rejected(make_provider, monkeypatch):
    from dataclasses import replace

    provider = make_provider(lambda _: httpx.Response(200, json=payload([bar()])))
    history = provider.get_candles("EXPLICIT_MAPPING", START, START + timedelta(minutes=1))
    leaked = replace(
        history,
        candles=(
            history.candles[0].model_copy(update={"event_time": START + timedelta(minutes=1)}),
        ),
    )
    monkeypatch.setattr(provider, "get_candles", lambda *_: leaked)
    with pytest.raises(NativeDataError, match="SESSION_BOUNDARY_LEAKAGE"):
        provider.get_session_open("EXPLICIT_MAPPING", START.date())
