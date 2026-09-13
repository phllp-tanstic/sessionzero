"""Add historical coverage profiles and precise manifest availability counts.

Revision ID: 20260913_05
Revises: 20260913_04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_05"
down_revision: str | None = "20260913_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "historical_ingestion_manifest_entries",
        sa.Column(
            "records_available_for_requested_window",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "historical_coverage_profiles",
        sa.Column("profile_version", sa.String(64), primary_key=True),
        sa.Column(
            "universe_version",
            sa.String(64),
            sa.ForeignKey("universe_snapshots.universe_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("transformation_version", sa.String(64), nullable=False),
        sa.Column("evaluation_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("minimum_total_history_days", sa.Integer(), nullable=False),
        sa.Column("minimum_oos_days", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "historical_coverage_members",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_version",
            sa.String(64),
            sa.ForeignKey("historical_coverage_profiles.profile_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("native_ticker", sa.String(32), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("transformation_version", sa.String(64), nullable=False),
        sa.Column("evaluation_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("earliest_observed_event_time", sa.DateTime(timezone=True)),
        sa.Column("latest_observed_event_time", sa.DateTime(timezone=True)),
        sa.Column("observed_duration_days", sa.Numeric(12, 6), nullable=False),
        sa.Column("observed_record_count", sa.Integer(), nullable=False),
        sa.Column("expected_intervals_where_session_known", sa.Integer(), nullable=False),
        sa.Column("missing_while_expected_open", sa.Integer(), nullable=False),
        sa.Column("source_session_unknown_count", sa.Integer(), nullable=False),
        sa.Column("quality_status", sa.String(16)),
        sa.Column("coverage_status", sa.String(40), nullable=False),
        sa.Column("minimum_total_history_days", sa.Integer(), nullable=False),
        sa.Column("minimum_oos_days", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("rate_limit_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(128)),
        sa.Column("verification_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "universe_version",
            sa.String(64),
            sa.ForeignKey("universe_snapshots.universe_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "coverage_status IN ('SUFFICIENT_MINIMUM_HISTORY', 'INSUFFICIENT_HISTORY', "
            "'SOURCE_SESSION_TOO_UNKNOWN', 'DATA_QUALITY_FAILURE', 'HISTORY_UNAVAILABLE', "
            "'UNKNOWN')",
            name="ck_coverage_member_status",
        ),
        sa.UniqueConstraint("profile_version", "symbol", name="uq_coverage_member_symbol"),
    )
    op.create_index(
        "ix_coverage_member_status",
        "historical_coverage_members",
        ["profile_version", "coverage_status"],
    )


def downgrade() -> None:
    op.drop_table("historical_coverage_members")
    op.drop_table("historical_coverage_profiles")
    op.drop_column(
        "historical_ingestion_manifest_entries", "records_available_for_requested_window"
    )
