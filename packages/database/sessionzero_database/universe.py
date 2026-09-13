from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sessionzero_bitget import (
    BitgetMarketClient,
    BitgetProviderError,
    HistoryPaginationError,
    fetch_bounded_history,
)
from sessionzero_market_data import CuratedBitgetSourceSessionProvider
from sessionzero_schemas import (
    HistoricalIngestionManifest,
    HistoricalManifestEntry,
    ManifestEntryStatus,
    QualityStatus,
    RealityUniverseSnapshot,
)
from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from .models import (
    HistoricalIngestionManifestEntryRow,
    HistoricalIngestionManifestRow,
    UniverseDiscoveryObservationRow,
    UniverseSnapshotMemberRow,
    UniverseSnapshotRow,
)
from .persistence import ingest_candle_observations

MANIFEST_TRANSFORMATION_VERSION = "reality_history_manifest.v1"
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SnapshotPersistenceResult:
    snapshot_written: bool
    members_written: int
    observation_id: uuid.UUID


def persist_universe_snapshot(
    engine: Engine, snapshot: RealityUniverseSnapshot
) -> SnapshotPersistenceResult:
    observation_id = uuid.uuid4()
    with engine.begin() as connection:
        root = connection.execute(
            postgresql_insert(UniverseSnapshotRow)
            .values(
                universe_version=snapshot.universe_version,
                schema_version=snapshot.schema_version,
                transformation_version=snapshot.transformation_version,
                generated_at=snapshot.generated_at,
                source=snapshot.source,
                source_endpoint=snapshot.source_endpoint,
                source_version=snapshot.source_version,
                interval=snapshot.interval,
            )
            .on_conflict_do_nothing(index_elements=["universe_version"])
            .returning(UniverseSnapshotRow.universe_version)
        )
        snapshot_written = root.scalar_one_or_none() is not None
        member_values = [
            {
                "universe_version": snapshot.universe_version,
                **member.model_dump(mode="python"),
                "mapping_status": member.mapping_status.value,
                "exclusion_reasons": [item.value for item in member.exclusion_reasons],
                "trading_periods": list(member.trading_periods),
            }
            for member in snapshot.members
        ]
        members = connection.execute(
            postgresql_insert(UniverseSnapshotMemberRow)
            .values(member_values)
            .on_conflict_do_nothing(constraint="uq_universe_member_symbol")
            .returning(UniverseSnapshotMemberRow.id)
        )
        members_written = len(members.scalars().all())
        connection.execute(
            postgresql_insert(UniverseDiscoveryObservationRow).values(
                observation_id=observation_id,
                universe_version=snapshot.universe_version,
                observed_at=snapshot.generated_at,
                raw_provider_payload=snapshot.raw_provider_payload,
            )
        )
    return SnapshotPersistenceResult(snapshot_written, members_written, observation_id)


def _manifest_version(
    universe_version: str, git_commit: str, entries: tuple[HistoricalManifestEntry, ...]
) -> str:
    return _hash(
        {
            "universe_version": universe_version,
            "transformation_version": MANIFEST_TRANSFORMATION_VERSION,
            "git_commit": git_commit,
            "entries": [entry.model_dump(mode="json") for entry in entries],
        }
    )


def ingest_manifest_subset(
    engine: Engine,
    client: BitgetMarketClient,
    snapshot: RealityUniverseSnapshot,
    *,
    start: datetime,
    end: datetime,
    subset_size: int,
    git_commit: str,
    page_limit: int = 100,
    max_pages: int = 100,
    clock: Clock = _utc_now,
) -> HistoricalIngestionManifest:
    if not 1 <= subset_size <= 20:
        raise ValueError("subset_size must be between 1 and 20")
    selected = tuple(member for member in snapshot.members if member.technically_eligible)[
        :subset_size
    ]
    if not selected:
        raise ValueError("universe contains no technically eligible members")
    source_sessions = CuratedBitgetSourceSessionProvider()
    entries: list[HistoricalManifestEntry] = []
    for member in selected:
        try:
            history = fetch_bounded_history(
                client,
                symbol=member.reality_symbol,
                interval=snapshot.interval,
                start=start,
                end=end,
                page_limit=page_limit,
                max_pages=max_pages,
                source_session_provider=source_sessions,
            )
            quality = history.quality
            if quality.quality_status == QualityStatus.FAIL:
                entries.append(
                    _quality_entry(
                        member.reality_symbol,
                        member.native_ticker,
                        quality,
                        normalized_written=0,
                        run_id=None,
                        status=ManifestEntryStatus.FAILED,
                        failure_code="DATA_QUALITY_FAILURE",
                    )
                )
                continue
            result = ingest_candle_observations(
                engine,
                history.observations,
                operation="universe_manifest_history",
                records_received=quality.records_received,
                requested_start=quality.requested_start,
                requested_end=quality.requested_end,
                interval=quality.interval,
                pages_requested=quality.page_count,
                quality_status=quality.quality_status.value,
            )
            entries.append(
                _quality_entry(
                    member.reality_symbol,
                    member.native_ticker,
                    quality,
                    normalized_written=result.normalized_records_written,
                    run_id=str(result.run_id),
                    status=(
                        ManifestEntryStatus.SUCCEEDED_WITH_WARNINGS
                        if quality.quality_status == QualityStatus.WARN
                        else ManifestEntryStatus.SUCCEEDED
                    ),
                    failure_code=None,
                )
            )
        except HistoryPaginationError as exc:
            entries.append(
                _quality_entry(
                    member.reality_symbol,
                    member.native_ticker,
                    exc.report,
                    normalized_written=0,
                    run_id=None,
                    status=ManifestEntryStatus.FAILED,
                    failure_code=exc.code,
                )
            )
        except BitgetProviderError as exc:
            entries.append(
                HistoricalManifestEntry(
                    symbol=member.reality_symbol,
                    native_ticker=member.native_ticker,
                    interval=snapshot.interval,
                    requested_start=start.astimezone(UTC),
                    requested_end=end.astimezone(UTC),
                    page_count=0,
                    raw_records_received=0,
                    normalized_records_written=0,
                    missing_while_expected_open=0,
                    source_session_unknown=0,
                    status=ManifestEntryStatus.UNAVAILABLE,
                    failure_code=exc.kind,
                )
            )
        except ValueError:
            entries.append(
                HistoricalManifestEntry(
                    symbol=member.reality_symbol,
                    native_ticker=member.native_ticker,
                    interval=snapshot.interval,
                    requested_start=start.astimezone(UTC),
                    requested_end=end.astimezone(UTC),
                    page_count=0,
                    raw_records_received=0,
                    normalized_records_written=0,
                    missing_while_expected_open=0,
                    source_session_unknown=0,
                    status=ManifestEntryStatus.FAILED,
                    failure_code="INGESTION_VALIDATION_FAILURE",
                )
            )
    normalized_entries = tuple(entries)
    generated_at = clock().astimezone(UTC)
    return HistoricalIngestionManifest(
        manifest_version=_manifest_version(
            snapshot.universe_version, git_commit, normalized_entries
        ),
        universe_version=snapshot.universe_version,
        transformation_version=MANIFEST_TRANSFORMATION_VERSION,
        git_commit=git_commit,
        generated_at=generated_at,
        entries=normalized_entries,
    )


def _quality_entry(
    symbol: str,
    native_ticker: str | None,
    quality: object,
    *,
    normalized_written: int,
    run_id: str | None,
    status: ManifestEntryStatus,
    failure_code: str | None,
) -> HistoricalManifestEntry:
    return HistoricalManifestEntry(
        symbol=symbol,
        native_ticker=native_ticker,
        interval=quality.interval,
        requested_start=quality.requested_start,
        requested_end=quality.requested_end,
        observed_start=quality.observed_start,
        observed_end=quality.observed_end,
        page_count=quality.page_count,
        raw_records_received=quality.records_received,
        normalized_records_written=normalized_written,
        quality_status=quality.quality_status.value,
        missing_while_expected_open=quality.missing_count,
        source_session_unknown=quality.source_session_unknown_count,
        ingestion_run_id=run_id,
        status=status,
        failure_code=failure_code,
    )


def persist_historical_manifest(engine: Engine, manifest: HistoricalIngestionManifest) -> bool:
    with engine.begin() as connection:
        root = connection.execute(
            postgresql_insert(HistoricalIngestionManifestRow)
            .values(
                manifest_version=manifest.manifest_version,
                universe_version=manifest.universe_version,
                transformation_version=manifest.transformation_version,
                git_commit=manifest.git_commit,
                generated_at=manifest.generated_at,
            )
            .on_conflict_do_nothing(index_elements=["manifest_version"])
            .returning(HistoricalIngestionManifestRow.manifest_version)
        )
        written = root.scalar_one_or_none() is not None
        if written:
            connection.execute(
                postgresql_insert(HistoricalIngestionManifestEntryRow).values(
                    [
                        {
                            "manifest_version": manifest.manifest_version,
                            **entry.model_dump(mode="python"),
                            "status": entry.status.value,
                            "ingestion_run_id": (
                                uuid.UUID(entry.ingestion_run_id)
                                if entry.ingestion_run_id is not None
                                else None
                            ),
                        }
                        for entry in manifest.entries
                    ]
                )
            )
    return written
