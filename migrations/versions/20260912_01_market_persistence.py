"""Create the Phase 1 market persistence foundation.

Revision ID: 20260912_01
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_written", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("records_received >= 0", name="ck_run_records_received_nonnegative"),
        sa.CheckConstraint("records_written >= 0", name="ck_run_records_written_nonnegative"),
        sa.CheckConstraint("status IN ('RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_run_status"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "normalized_market_candles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(), nullable=False),
        sa.Column("high", sa.Numeric(), nullable=False),
        sa.Column("low", sa.Numeric(), nullable=False),
        sa.Column("close", sa.Numeric(), nullable=False),
        sa.Column("volume", sa.Numeric(), nullable=True),
        sa.Column("turnover", sa.Numeric(), nullable=True),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("high >= low", name="ck_candle_high_gte_low"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "symbol",
            "market",
            "interval",
            "event_time",
            name="uq_normalized_candle_market_identity",
        ),
    )
    op.create_index(
        "ix_normalized_candle_lookup",
        "normalized_market_candles",
        ["symbol", "interval", "event_time"],
    )
    op.create_table(
        "raw_market_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["run_id"], ["ingestion_runs.run_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "source",
            "symbol",
            "market",
            "endpoint",
            "event_time",
            name="uq_raw_observation_per_run",
        ),
    )
    op.create_index(
        "ix_raw_market_identity",
        "raw_market_observations",
        ["source", "symbol", "market", "event_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_market_identity", table_name="raw_market_observations")
    op.drop_table("raw_market_observations")
    op.drop_index("ix_normalized_candle_lookup", table_name="normalized_market_candles")
    op.drop_table("normalized_market_candles")
    op.drop_table("ingestion_runs")
