"""Append-only prospective next-open outcome collection and linkage."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from sessionzero_config import get_settings
from sessionzero_market_data import XnysTradingCalendar
from sessionzero_market_data.alpaca import AlpacaNativeEquityProvider
from sessionzero_schemas import ProspectiveOutcomeRetrieval, canonical_digest
from sqlalchemy import Engine, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .capture_cli import git_commit
from .dataset_artifacts import load_cohort
from .engine import create_database_engine, verify_database_connection
from .models import (
    DecisionOutcomeLink,
    DecisionTimeSnapshotRow,
    ProspectiveOutcomeCaptureRun,
    ProspectiveOutcomeRetrievalRow,
    ProspectiveOutcomeVersion,
)

OUTCOME_AVAILABILITY_DELAY = timedelta(minutes=17)


class OutcomeProviderFailure(RuntimeError):
    def __init__(self, completed_symbols: int) -> None:
        super().__init__("OUTCOME_PROVIDER_FAILURE")
        self.completed_symbols = completed_symbols


def _outcome_retrieval(
    provider: AlpacaNativeEquityProvider,
    *,
    reality_symbol: str,
    decision_timestamp: datetime,
    scheduled_open: datetime,
    commit: str,
) -> ProspectiveOutcomeRetrieval:
    request_time = datetime.now(UTC)
    history = provider.get_candles(
        reality_symbol, scheduled_open, scheduled_open + timedelta(minutes=1)
    )
    if len(history.candles) != 1 or len(history.pages) != 1:
        raise ValueError(f"no unique next opening minute for {reality_symbol}")
    candle, page = history.candles[0], history.pages[0]
    if candle.event_time != scheduled_open:
        raise ValueError("outcome is not the exact first regular-session minute")
    raw = json.loads(page.body, parse_float=str, parse_int=str)
    return ProspectiveOutcomeRetrieval(
        reality_symbol=reality_symbol,
        native_ticker=candle.native_ticker,
        endpoint=page.endpoint,
        decision_timestamp=decision_timestamp,
        event_time=candle.event_time,
        request_time=request_time,
        ingestion_time=page.ingestion_time,
        provider_identifiers={
            key: value
            for key, value in page.response_headers.items()
            if key in {"x-request-id", "date", "x-ratelimit-limit", "x-ratelimit-remaining"}
        },
        raw_response=raw,
        canonical_value={"open": str(candle.open), "feed": "sip", "adjustment": "raw"},
        git_commit=commit,
    )


def persist_prospective_outcomes(
    engine: Engine,
    *,
    capture_id: uuid.UUID,
    snapshot_version: str,
    decision_timestamp: datetime,
    scheduled_open: datetime,
    started_at: datetime,
    completed_at: datetime,
    retrievals: tuple[ProspectiveOutcomeRetrieval, ...],
) -> dict[str, int | str]:
    if not retrievals or completed_at < started_at:
        raise ValueError("invalid outcome persistence boundary")
    if any(item.decision_timestamp != decision_timestamp for item in retrievals):
        raise ValueError("outcome decision identity mismatch")
    capture_version = canonical_digest(sorted(item.retrieval_hash for item in retrievals))
    with engine.begin() as connection:
        connection.execute(select(func.pg_advisory_xact_lock(-int(decision_timestamp.timestamp()))))
        stored_snapshot = connection.execute(
            select(
                DecisionTimeSnapshotRow.snapshot_version,
                DecisionTimeSnapshotRow.mapping_version,
                DecisionTimeSnapshotRow.source_session_evidence,
            ).where(
                DecisionTimeSnapshotRow.snapshot_version == snapshot_version,
                DecisionTimeSnapshotRow.decision_timestamp == decision_timestamp,
            )
        ).one_or_none()
        if stored_snapshot is None:
            raise ValueError("decision snapshot does not exist")
        if any(
            item.reality_symbol not in stored_snapshot.source_session_evidence
            for item in retrievals
        ):
            raise ValueError("outcome symbol was not captured in the decision snapshot")
        same_capture = connection.execute(
            select(ProspectiveOutcomeCaptureRun.capture_id).where(
                ProspectiveOutcomeCaptureRun.capture_version == capture_version
            )
        ).scalar_one_or_none()
        if same_capture is not None:
            return {
                "capture_id": str(same_capture),
                "snapshot_version": snapshot_version,
                "retrievals_written": 0,
                "outcome_versions_written": 0,
                "outcome_links_written": 0,
            }
        versions_written = 0
        for item in retrievals:
            inserted = connection.execute(
                pg_insert(ProspectiveOutcomeVersion)
                .values(
                    version_hash=item.version_hash,
                    logical_key_hash=item.logical_key_hash,
                    canonical_hash=item.canonical_hash,
                    source=item.source,
                    reality_symbol=item.reality_symbol,
                    native_ticker=item.native_ticker,
                    field_name=item.field_name,
                    role=item.role,
                    decision_timestamp=item.decision_timestamp,
                    event_time=item.event_time,
                    canonical_value=item.canonical_value,
                    collector_version=item.collector_version,
                    git_commit=item.git_commit,
                    first_request_time=item.request_time,
                    first_ingestion_time=item.ingestion_time,
                )
                .on_conflict_do_nothing(index_elements=["version_hash"])
                .returning(ProspectiveOutcomeVersion.version_hash)
            ).scalar_one_or_none()
            versions_written += inserted is not None
        connection.execute(
            insert(ProspectiveOutcomeCaptureRun).values(
                capture_id=capture_id,
                snapshot_version=snapshot_version,
                decision_timestamp=decision_timestamp,
                scheduled_open=scheduled_open,
                started_at=started_at,
                completed_at=completed_at,
                status="SUCCEEDED",
                collector_version=retrievals[0].collector_version,
                git_commit=retrievals[0].git_commit,
                capture_version=capture_version,
                symbol_count=len(retrievals),
            )
        )
        connection.execute(
            insert(ProspectiveOutcomeRetrievalRow),
            [
                {
                    "retrieval_hash": item.retrieval_hash,
                    "capture_id": capture_id,
                    "version_hash": item.version_hash,
                    "request_time": item.request_time,
                    "ingestion_time": item.ingestion_time,
                    "provider_identifiers": item.provider_identifiers,
                    "raw_response": item.raw_response,
                }
                for item in retrievals
            ],
        )
        links_written = 0
        linked_at = datetime.now(UTC)
        for item in retrievals:
            link_hash = canonical_digest(
                {"snapshot_version": snapshot_version, "outcome_version_hash": item.version_hash}
            )
            inserted = connection.execute(
                pg_insert(DecisionOutcomeLink)
                .values(
                    link_hash=link_hash,
                    snapshot_version=snapshot_version,
                    outcome_version_hash=item.version_hash,
                    reality_symbol=item.reality_symbol,
                    native_ticker=item.native_ticker,
                    linked_at=linked_at,
                )
                .on_conflict_do_nothing(index_elements=["link_hash"])
                .returning(DecisionOutcomeLink.link_hash)
            ).scalar_one_or_none()
            links_written += inserted is not None
    return {
        "capture_id": str(capture_id),
        "snapshot_version": snapshot_version,
        "retrievals_written": len(retrievals),
        "outcome_versions_written": versions_written,
        "outcome_links_written": links_written,
    }


def capture_outcome_iteration(*, decision_timestamp: datetime) -> dict[str, int | str]:
    started = datetime.now(UTC)
    cohort = load_cohort()
    calendar = XnysTradingCalendar()
    session = calendar.session_at(decision_timestamp)
    if session.regular_open - timedelta(hours=1) != decision_timestamp:
        raise ValueError("decision timestamp must be exactly 60 minutes before XNYS open")
    if started < session.regular_open + OUTCOME_AVAILABILITY_DELAY:
        raise ValueError("outcome is not yet safely available")
    engine = create_database_engine(get_settings().require_database_url())
    try:
        verify_database_connection(engine)
        with engine.connect() as connection:
            snapshot = connection.execute(
                select(
                    DecisionTimeSnapshotRow.snapshot_version,
                    DecisionTimeSnapshotRow.mapping_version,
                ).where(DecisionTimeSnapshotRow.decision_timestamp == decision_timestamp)
            ).one_or_none()
        if snapshot is None:
            raise ValueError("decision snapshot does not exist")
        if snapshot.mapping_version != cohort.cohort_version:
            raise ValueError("decision snapshot mapping identity mismatch")
        commit = git_commit()
        retrievals: list[ProspectiveOutcomeRetrieval] = []
        provider = AlpacaNativeEquityProvider(cohort)
        try:
            for member in cohort.members:
                try:
                    retrievals.append(
                        _outcome_retrieval(
                            provider,
                            reality_symbol=member.symbol,
                            decision_timestamp=decision_timestamp,
                            scheduled_open=session.regular_open,
                            commit=commit,
                        )
                    )
                except Exception:
                    raise OutcomeProviderFailure(len(retrievals)) from None
        finally:
            provider.close()
        return persist_prospective_outcomes(
            engine,
            capture_id=uuid.uuid4(),
            snapshot_version=snapshot.snapshot_version,
            decision_timestamp=decision_timestamp,
            scheduled_open=session.regular_open,
            started_at=started,
            completed_at=datetime.now(UTC),
            retrievals=tuple(retrievals),
        )
    finally:
        engine.dispose()
