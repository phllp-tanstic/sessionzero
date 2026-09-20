"""Explicit opt-in; credentials and the accepted persisted cohort are required."""

import os
from datetime import timedelta

import pytest
from sessionzero_bitget import derive_evidence_qualified_cohort
from sessionzero_config import get_settings
from sessionzero_database.coverage import load_accepted_universe
from sessionzero_database.engine import create_database_engine
from sessionzero_market_data import XnysTradingCalendar, load_bitget_source_session_evidence
from sessionzero_market_data.alpaca import native_provider


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("SESSIONZERO_RUN_LIVE_ALPACA") != "1",
    reason="set SESSIONZERO_RUN_LIVE_ALPACA=1 for authenticated SIP probes",
)
def test_live_accepted_pilot_sip():
    engine = create_database_engine(get_settings().require_database_url())
    provider = None
    try:
        universe = load_accepted_universe(engine, os.environ["NATIVE_UNIVERSE_VERSION"])
        cohort = derive_evidence_qualified_cohort(
            universe_version=universe.universe_version,
            universe_members=universe.members,
            evidence_dataset=load_bitget_source_session_evidence(),
        )
        assert cohort.cohort_version == os.environ["NATIVE_COHORT_VERSION"]
        assert len(cohort.members) == 21
        provider = native_provider(cohort)
        provider.page_limit = 2
        session = XnysTradingCalendar().session_at(cohort.evaluation_start)
        for ticker in ("AAPL", "NVDA", "TSLA"):
            member = next(m for m in cohort.members if m.native_ticker == ticker)
            history = provider.get_candles(
                member.symbol, session.next_cash_open, session.next_cash_open + timedelta(minutes=5)
            )
            assert len(history.pages) > 1 and history.candles
            assert all(c.feed == "sip" and c.adjustment == "raw" for c in history.candles)
            assert all(p.response_headers.get("x-request-id") for p in history.pages)
    finally:
        if provider:
            provider.close()
        engine.dispose()
