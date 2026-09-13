"""Add versioned Reality universes and historical manifests.

Revision ID: 20260913_04
Revises: 20260913_03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_04"
down_revision: str | None = "20260913_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "universe_snapshots",
        sa.Column("universe_version", sa.String(64), primary_key=True),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("transformation_version", sa.String(64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_endpoint", sa.String(255), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "universe_discovery_observations",
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "universe_version",
            sa.String(64),
            sa.ForeignKey("universe_snapshots.universe_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_provider_payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_universe_observation_version",
        "universe_discovery_observations",
        ["universe_version", "observed_at"],
    )
    op.create_table(
        "universe_snapshot_members",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "universe_version",
            sa.String(64),
            sa.ForeignKey("universe_snapshots.universe_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reality_symbol", sa.String(64), nullable=False),
        sa.Column("base_coin", sa.String(64), nullable=False),
        sa.Column("quote_coin", sa.String(64), nullable=False),
        sa.Column("native_ticker", sa.String(32)),
        sa.Column("instrument_status", sa.String(32), nullable=False),
        sa.Column("is_reality", sa.Boolean(), nullable=False),
        sa.Column("launch_time", sa.DateTime(timezone=True)),
        sa.Column("price_precision", sa.Integer()),
        sa.Column("quantity_precision", sa.Integer()),
        sa.Column("trading_periods", postgresql.JSONB(), nullable=False),
        sa.Column("weekend_tradable", sa.Boolean()),
        sa.Column("mapping_status", sa.String(16), nullable=False),
        sa.Column("source_session_status", sa.String(32), nullable=False),
        sa.Column("source_session_mode", sa.String(32), nullable=False),
        sa.Column("technically_eligible", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("raw_metadata_key", sa.String(64), nullable=False),
        sa.UniqueConstraint("universe_version", "reality_symbol", name="uq_universe_member_symbol"),
    )
    op.create_index(
        "ix_universe_member_eligibility",
        "universe_snapshot_members",
        ["universe_version", "technically_eligible"],
    )
    op.create_table(
        "historical_ingestion_manifests",
        sa.Column("manifest_version", sa.String(64), primary_key=True),
        sa.Column(
            "universe_version",
            sa.String(64),
            sa.ForeignKey("universe_snapshots.universe_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("transformation_version", sa.String(64), nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "historical_ingestion_manifest_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "manifest_version",
            sa.String(64),
            sa.ForeignKey("historical_ingestion_manifests.manifest_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("native_ticker", sa.String(32)),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("requested_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_start", sa.DateTime(timezone=True)),
        sa.Column("observed_end", sa.DateTime(timezone=True)),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("raw_records_received", sa.Integer(), nullable=False),
        sa.Column("normalized_records_written", sa.Integer(), nullable=False),
        sa.Column("quality_status", sa.String(16)),
        sa.Column("missing_while_expected_open", sa.Integer(), nullable=False),
        sa.Column("source_session_unknown", sa.Integer(), nullable=False),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_runs.run_id", ondelete="RESTRICT"),
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("failure_code", sa.String(128)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "manifest_version",
            "symbol",
            "interval",
            "requested_start",
            "requested_end",
            name="uq_manifest_entry_range",
        ),
    )


def downgrade() -> None:
    for table in (
        "historical_ingestion_manifest_entries",
        "historical_ingestion_manifests",
        "universe_snapshot_members",
        "universe_discovery_observations",
        "universe_snapshots",
    ):
        op.drop_table(table)
