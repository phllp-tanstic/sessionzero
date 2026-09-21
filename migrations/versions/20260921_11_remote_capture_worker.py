"""Remote worker runs, idempotent decisions, and append-only outcomes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260921_11"
down_revision = "20260920_10"
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
    op.create_unique_constraint(
        "uq_decision_snapshot_timestamp", "decision_time_snapshots", ["decision_timestamp"]
    )
    op.create_table(
        "prospective_worker_runs",
        sa.Column("worker_run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lateness_seconds", sa.Numeric(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("symbols_expected", sa.Integer(), nullable=False),
        sa.Column("symbols_captured", sa.Integer(), nullable=False),
        sa.Column("provider_status", postgresql.JSONB(), nullable=False),
        sa.Column("snapshot_version", sa.String(64), nullable=True),
        sa.Column("outcome_links", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("universe_version", sa.String(64), nullable=True),
        sa.Column("cohort_version", sa.String(64), nullable=True),
        sa.Column("mapping_version", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "operation IN ('DECISION','OUTCOME','TICK')", name="ck_worker_operation"
        ),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED','PARTIAL','FAILED','MISSED_DECISION_WINDOW',"
            "'PROVIDER_UNAVAILABLE','DATABASE_FAILURE','IDENTITY_MISMATCH',"
            "'SKIPPED_NO_ACTION')",
            name="ck_worker_status",
        ),
        sa.CheckConstraint("actual_start_time <= completed_at", name="ck_worker_time_order"),
        sa.CheckConstraint(
            "symbols_expected >= 0 AND symbols_captured >= 0 AND "
            "symbols_captured <= symbols_expected",
            name="ck_worker_symbol_counts",
        ),
        sa.CheckConstraint("outcome_links >= 0", name="ck_worker_outcome_links"),
    )
    op.create_index(
        "ix_worker_runs_latest", "prospective_worker_runs", ["actual_start_time"], unique=False
    )
    op.create_table(
        "prospective_outcome_capture_runs",
        sa.Column("capture_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_version",
            sa.String(64),
            sa.ForeignKey("decision_time_snapshots.snapshot_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_open", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("collector_version", sa.String(64), nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("capture_version", sa.String(64), nullable=False, unique=True),
        sa.Column("symbol_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("status = 'SUCCEEDED'", name="ck_outcome_capture_success"),
        sa.CheckConstraint("started_at <= completed_at", name="ck_outcome_capture_time_order"),
        sa.CheckConstraint("decision_timestamp < scheduled_open", name="ck_outcome_after_decision"),
        sa.CheckConstraint("symbol_count > 0", name="ck_outcome_symbol_count"),
    )
    op.create_table(
        "prospective_outcome_versions",
        sa.Column("version_hash", sa.String(64), primary_key=True),
        sa.Column("logical_key_hash", sa.String(64), nullable=False),
        sa.Column("canonical_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("reality_symbol", sa.String(64), nullable=False),
        sa.Column("native_ticker", sa.String(32), nullable=False),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canonical_value", postgresql.JSONB(), nullable=False),
        sa.Column("collector_version", sa.String(64), nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("first_request_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "logical_key_hash", "canonical_hash", name="uq_outcome_logical_content_version"
        ),
        sa.CheckConstraint("field_name = 'FIRST_1M_BAR_OPEN'", name="ck_outcome_field"),
        sa.CheckConstraint("role = 'FUTURE_OUTCOME'", name="ck_outcome_role"),
        sa.CheckConstraint("decision_timestamp < event_time", name="ck_outcome_event_order"),
        sa.CheckConstraint(
            "event_time <= first_request_time AND first_request_time <= first_ingestion_time",
            name="ck_outcome_availability_order",
        ),
    )
    op.create_table(
        "prospective_outcome_retrievals",
        sa.Column("retrieval_hash", sa.String(64), primary_key=True),
        sa.Column(
            "capture_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prospective_outcome_capture_runs.capture_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "version_hash",
            sa.String(64),
            sa.ForeignKey("prospective_outcome_versions.version_hash", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("request_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_identifiers", postgresql.JSONB(), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("request_time <= ingestion_time", name="ck_outcome_retrieval_order"),
    )
    op.create_table(
        "decision_outcome_links",
        sa.Column("link_hash", sa.String(64), primary_key=True),
        sa.Column(
            "snapshot_version",
            sa.String(64),
            sa.ForeignKey("decision_time_snapshots.snapshot_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "outcome_version_hash",
            sa.String(64),
            sa.ForeignKey("prospective_outcome_versions.version_hash", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reality_symbol", sa.String(64), nullable=False),
        sa.Column("native_ticker", sa.String(32), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "snapshot_version", "outcome_version_hash", name="uq_snapshot_outcome_version"
        ),
    )
    op.create_index(
        "ix_decision_outcome_latest",
        "decision_outcome_links",
        ["snapshot_version", "native_ticker", "linked_at"],
        unique=False,
    )
    for table in (
        "prospective_worker_runs",
        "prospective_outcome_capture_runs",
        "prospective_outcome_versions",
        "prospective_outcome_retrievals",
        "decision_outcome_links",
    ):
        _immutable_trigger(table)


def downgrade() -> None:
    for table in (
        "decision_outcome_links",
        "prospective_outcome_retrievals",
        "prospective_outcome_versions",
        "prospective_outcome_capture_runs",
        "prospective_worker_runs",
    ):
        op.drop_table(table)
    op.drop_constraint("uq_decision_snapshot_timestamp", "decision_time_snapshots", type_="unique")
