"""Transactional append-only persistence for point-in-time capture evidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sessionzero_schemas import DecisionTimeSnapshot, ProspectiveRetrieval, canonical_digest
from sqlalchemy import Engine, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import (
    DecisionTimeSnapshotRow,
    PointInTimeCaptureRun,
    PointInTimeObservationVersion,
    PointInTimeRetrieval,
)


def persist_point_in_time_capture(
    engine: Engine,
    *,
    capture_id: uuid.UUID,
    started_at: datetime,
    completed_at: datetime,
    retrievals: tuple[ProspectiveRetrieval, ...],
    snapshot: DecisionTimeSnapshot,
) -> dict[str, int | str]:
    if not retrievals or completed_at < started_at:
        raise ValueError("invalid capture persistence boundary")
    if snapshot.capture_version != canonical_digest(
        sorted(item.retrieval_hash for item in retrievals)
    ):
        raise ValueError("capture version does not match retrieval evidence")
    if any(item.ingestion_time > snapshot.decision_timestamp for item in retrievals):
        raise ValueError("post-decision evidence cannot be persisted in a snapshot")

    version_rows = [
        {
            "version_hash": item.version_hash,
            "logical_key_hash": item.logical_key_hash,
            "canonical_hash": item.canonical_hash,
            "source": item.source,
            "symbol": item.symbol,
            "endpoint": item.endpoint,
            "field_name": item.field_name,
            "role": item.role,
            "event_time": item.event_time,
            "canonical_value": item.canonical_value,
            "collector_version": item.collector_version,
            "git_commit": item.git_commit,
            "first_request_time": item.request_time,
            "first_ingestion_time": item.ingestion_time,
        }
        for item in retrievals
    ]
    with engine.begin() as connection:
        connection.execute(
            select(func.pg_advisory_xact_lock(int(snapshot.decision_timestamp.timestamp())))
        )
        same_capture = connection.execute(
            select(PointInTimeCaptureRun.capture_id).where(
                PointInTimeCaptureRun.capture_version == snapshot.capture_version
            )
        ).scalar_one_or_none()
        existing_snapshot = connection.scalar(
            select(DecisionTimeSnapshotRow.snapshot_version).where(
                DecisionTimeSnapshotRow.decision_timestamp == snapshot.decision_timestamp
            )
        )
        if same_capture is not None:
            return {
                "capture_id": str(same_capture),
                "snapshot_version": existing_snapshot or snapshot.snapshot_version,
                "retrievals_written": 0,
                "observation_versions_written": 0,
                "snapshot_created": False,
            }
        inserted = 0
        for row in version_rows:
            result = connection.execute(
                pg_insert(PointInTimeObservationVersion)
                .values(**row)
                .on_conflict_do_nothing(index_elements=["version_hash"])
                .returning(PointInTimeObservationVersion.version_hash)
            )
            inserted += result.scalar_one_or_none() is not None
        connection.execute(
            insert(PointInTimeCaptureRun).values(
                capture_id=capture_id,
                decision_timestamp=snapshot.decision_timestamp,
                started_at=started_at,
                completed_at=completed_at,
                status="SUCCEEDED",
                collector_version=retrievals[0].collector_version,
                git_commit=retrievals[0].git_commit,
                dataset_version=snapshot.dataset_version,
                calendar_version=snapshot.calendar_version,
                mapping_version=snapshot.mapping_version,
                source_session_evidence_version=snapshot.source_session_evidence_version,
                capture_version=snapshot.capture_version,
                symbol_count=sum(item.field_name == "REALITY_DECISION_MARK" for item in retrievals),
            )
        )
        connection.execute(
            insert(PointInTimeRetrieval),
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
        if existing_snapshot is None:
            connection.execute(
                insert(DecisionTimeSnapshotRow).values(
                    **snapshot.model_dump(mode="python"),
                    capture_id=capture_id,
                    created_at=datetime.now(UTC),
                )
            )
        snapshot_version = existing_snapshot or snapshot.snapshot_version
    return {
        "capture_id": str(capture_id),
        "snapshot_version": snapshot_version,
        "retrievals_written": len(retrievals),
        "observation_versions_written": inserted,
        "snapshot_created": existing_snapshot is None,
    }
