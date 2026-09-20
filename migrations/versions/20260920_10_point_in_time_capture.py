"""Immutable prospective point-in-time captures and decision snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260920_10"
down_revision = "20260920_09"
branch_labels = None
depends_on = None


def _immutable_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER {table}_immutable
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION reject_point_in_time_mutation()
        """
    )


def upgrade() -> None:
    op.create_table(
        "point_in_time_capture_runs",
        sa.Column("capture_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("collector_version", sa.String(64), nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("dataset_version", sa.String(64), nullable=False),
        sa.Column("calendar_version", sa.String(64), nullable=False),
        sa.Column("mapping_version", sa.String(64), nullable=False),
        sa.Column("source_session_evidence_version", sa.String(64), nullable=False),
        sa.Column("capture_version", sa.String(64), nullable=False, unique=True),
        sa.Column("symbol_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("status = 'SUCCEEDED'", name="ck_pit_capture_success"),
        sa.CheckConstraint("started_at <= completed_at", name="ck_pit_capture_time_order"),
        sa.CheckConstraint("symbol_count > 0", name="ck_pit_capture_symbol_count"),
    )
    op.create_table(
        "point_in_time_observation_versions",
        sa.Column("version_hash", sa.String(64), primary_key=True),
        sa.Column("logical_key_hash", sa.String(64), nullable=False),
        sa.Column("canonical_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canonical_value", postgresql.JSONB(), nullable=False),
        sa.Column("collector_version", sa.String(64), nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("first_request_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "logical_key_hash", "canonical_hash", name="uq_pit_logical_content_version"
        ),
        sa.CheckConstraint("role = 'FEATURE'", name="ck_pit_observation_feature_only"),
        sa.CheckConstraint(
            "field_name IN ('REALITY_DECISION_MARK','PREVIOUS_NATIVE_CLOSE')",
            name="ck_pit_observation_field",
        ),
        sa.CheckConstraint(
            "first_ingestion_time >= first_request_time", name="ck_pit_observation_time_order"
        ),
    )
    op.create_table(
        "point_in_time_retrievals",
        sa.Column("retrieval_hash", sa.String(64), primary_key=True),
        sa.Column(
            "capture_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("point_in_time_capture_runs.capture_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "version_hash",
            sa.String(64),
            sa.ForeignKey("point_in_time_observation_versions.version_hash", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("request_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_identifiers", postgresql.JSONB(), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("ingestion_time >= request_time", name="ck_pit_retrieval_time_order"),
    )
    op.create_table(
        "decision_time_snapshots",
        sa.Column("snapshot_version", sa.String(64), primary_key=True),
        sa.Column(
            "capture_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("point_in_time_capture_runs.capture_id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("transformation_version", sa.String(64), nullable=False),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reality_observation_versions", postgresql.JSONB(), nullable=False),
        sa.Column("previous_close_versions", postgresql.JSONB(), nullable=False),
        sa.Column("source_session_evidence", postgresql.JSONB(), nullable=False),
        sa.Column("source_session_evidence_version", sa.String(64), nullable=False),
        sa.Column("calendar_version", sa.String(64), nullable=False),
        sa.Column("mapping_version", sa.String(64), nullable=False),
        sa.Column("dataset_version", sa.String(64), nullable=False),
        sa.Column("capture_version", sa.String(64), nullable=False),
        sa.Column("contains_future_outcome", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "contains_future_outcome = false", name="ck_decision_snapshot_no_future_outcome"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION reject_point_in_time_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'point-in-time evidence is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in (
        "point_in_time_capture_runs",
        "point_in_time_observation_versions",
        "point_in_time_retrievals",
        "decision_time_snapshots",
    ):
        _immutable_trigger(table)


def downgrade() -> None:
    for table in (
        "decision_time_snapshots",
        "point_in_time_retrievals",
        "point_in_time_observation_versions",
        "point_in_time_capture_runs",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION reject_point_in_time_mutation()")
