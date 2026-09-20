from types import SimpleNamespace

import pytest
from sessionzero_bitget import derive_evidence_qualified_cohort
from sessionzero_database.native_cohort import reverify_native_cohort
from sessionzero_market_data import load_bitget_source_session_evidence
from sessionzero_market_data.native import NativeDataError
from sessionzero_schemas import UniverseMember


def test_evidence_mapping_reverification_preserves_existing_hash_contract():
    dataset = load_bitget_source_session_evidence()
    record = next(
        r for r in dataset.evidence if r.evidence_id == "bitget.2026-06-12.weekend-batch-21"
    )
    # Synthetic ticker values test the independent existing derivation, not live coverage.
    members = tuple(
        UniverseMember(
            reality_symbol=symbol,
            base_coin="test",
            quote_coin="USDT",
            native_ticker="TEST",
            instrument_status="online",
            is_reality=True,
            mapping_status="AVAILABLE",
            source_session_status="UNKNOWN",
            source_session_mode="UNKNOWN",
            technically_eligible=True,
            exclusion_reasons=(),
            raw_metadata_key="a" * 64,
        )
        for symbol in sorted(record.symbols)
    )
    expected = derive_evidence_qualified_cohort(
        universe_version="b" * 64,
        universe_members=members,
        evidence_dataset=dataset,
    )
    calls = []

    def mapping(symbol):
        calls.append(symbol)
        return SimpleNamespace(native_ticker="TEST"), (symbol,)

    provider = SimpleNamespace(get_mapping=mapping)
    cohort, raw = reverify_native_cohort(
        provider,
        evidence_id=record.evidence_id,
        original_universe_version="b" * 64,
        expected_cohort_version=expected.cohort_version,
    )
    assert cohort == expected
    assert calls == sorted(record.symbols) and len(raw) == 21
    with pytest.raises(NativeDataError, match="HASH_MISMATCH"):
        reverify_native_cohort(
            provider,
            evidence_id=record.evidence_id,
            original_universe_version="c" * 64,
            expected_cohort_version=expected.cohort_version,
        )
    provider.get_mapping = lambda _: (SimpleNamespace(native_ticker="CHANGED"), ())
    with pytest.raises(NativeDataError, match="HASH_MISMATCH"):
        reverify_native_cohort(
            provider,
            evidence_id=record.evidence_id,
            original_universe_version="b" * 64,
            expected_cohort_version=expected.cohort_version,
        )


def test_unknown_evidence_stops_before_mapping_requests():
    provider = SimpleNamespace(get_mapping=lambda _: pytest.fail("must not call"))
    with pytest.raises(NativeDataError, match="MEMBERSHIP_EVIDENCE"):
        reverify_native_cohort(
            provider,
            evidence_id="missing",
            original_universe_version="b" * 64,
            expected_cohort_version="a" * 64,
        )
