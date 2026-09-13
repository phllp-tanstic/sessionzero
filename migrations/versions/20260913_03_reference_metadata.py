"""Add auditable Bitget reference metadata persistence.

Revision ID: 20260913_03
Revises: 20260912_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_03"
down_revision: str | None = "20260912_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column:
    return sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True)


def _provenance() -> list[sa.Column]:
    return [
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("provider_record_key", sa.String(64), nullable=False),
        sa.Column("availability_time", sa.DateTime(timezone=True)),
        sa.Column("availability_time_status", sa.String(16), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("raw_or_derived", sa.String(16), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "raw_reference_observations",
        _id(),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_runs.run_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_params", postgresql.JSONB(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("provider_request_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_record_key", sa.String(64), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "run_id", "provider_record_key", name="uq_raw_reference_response_per_run"
        ),
    )
    op.create_index(
        "ix_raw_reference_endpoint",
        "raw_reference_observations",
        ["endpoint", "provider_request_time"],
    )
    op.create_table(
        "reality_symbol_mappings",
        _id(),
        *_provenance(),
        sa.Column("reality_symbol", sa.String(64), nullable=False),
        sa.Column("base_coin", sa.String(64), nullable=False),
        sa.Column("native_ticker", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("trading_periods", postgresql.JSONB(), nullable=False),
        sa.Column("weekend_tradable", sa.Boolean(), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True)),
        sa.Column("permanent_identifier", sa.String(128)),
        sa.UniqueConstraint("source", "provider_record_key", name="uq_reality_mapping_version"),
    )
    op.create_index(
        "ix_reality_mapping_lookup", "reality_symbol_mappings", ["reality_symbol", "ingestion_time"]
    )
    op.create_table(
        "corporate_actions",
        _id(),
        *_provenance(),
        sa.Column("native_ticker", sa.String(32)),
        sa.Column("provider_symbol", sa.String(64)),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("announcement_date", sa.Date()),
        sa.Column("record_date", sa.Date()),
        sa.Column("ex_date", sa.Date()),
        sa.Column("payment_date", sa.Date()),
        sa.Column("effective_date", sa.Date()),
        sa.Column("cash_amount_per_share", sa.Numeric()),
        sa.Column("stock_amount_per_share", sa.Numeric()),
        sa.Column("currency", sa.String(16)),
        sa.Column("numerator", sa.Numeric()),
        sa.Column("denominator", sa.Numeric()),
        sa.Column("adjustment_ratio", sa.Numeric()),
        sa.Column("provider_status", sa.String(32)),
        sa.Column("event_timezone", sa.String(32)),
        sa.Column("trading_halt_start", sa.DateTime(timezone=True)),
        sa.Column("trading_halt_end", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "action_type IN ('CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'REVERSE_SPLIT')",
            name="ck_corporate_action_type",
        ),
        sa.UniqueConstraint("source", "provider_record_key", name="uq_corporate_action_version"),
    )
    op.create_index(
        "ix_corporate_action_lookup", "corporate_actions", ["native_ticker", "effective_date"]
    )
    op.create_table(
        "share_capital_changes",
        _id(),
        *_provenance(),
        sa.Column("native_ticker", sa.String(32), nullable=False),
        sa.Column("announcement_date", sa.Date()),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("total_shares", sa.Numeric(), nullable=False),
        sa.Column("common_shares", sa.Numeric(), nullable=False),
        sa.Column("preferred_shares", sa.Numeric()),
        sa.Column("other_shares", sa.Numeric()),
        sa.Column("special_explanation", sa.String()),
        sa.Column("change_reason", sa.String()),
        sa.UniqueConstraint("source", "provider_record_key", name="uq_share_capital_version"),
    )
    op.create_index(
        "ix_share_capital_lookup", "share_capital_changes", ["native_ticker", "effective_date"]
    )
    op.create_table(
        "suspension_records",
        _id(),
        *_provenance(),
        sa.Column("native_ticker", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("suspension_date", sa.Date(), nullable=False),
        sa.Column("suspension_time", sa.String(16)),
        sa.Column("suspension_reason", sa.String()),
        sa.Column("suspension_price", sa.Numeric()),
        sa.Column("resumption_date", sa.Date()),
        sa.Column("resumption_quote_time", sa.String(16)),
        sa.Column("resumption_trading_time", sa.String(16)),
        sa.Column("event_timezone", sa.String(32)),
        sa.UniqueConstraint("source", "provider_record_key", name="uq_suspension_version"),
    )
    op.create_index(
        "ix_suspension_lookup", "suspension_records", ["native_ticker", "suspension_date"]
    )
    op.create_table(
        "source_session_metadata",
        _id(),
        *_provenance(),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("daylight_type", sa.String(16), nullable=False),
        sa.Column("state_time_zone", sa.String(32), nullable=False),
        sa.Column("calendar_time_zone", sa.String(32), nullable=False),
        sa.Column("sessions", postgresql.JSONB(), nullable=False),
        sa.Column("closures", postgresql.JSONB(), nullable=False),
        sa.Column("regular_closure_days", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("source", "provider_record_key", name="uq_source_session_version"),
    )
    op.create_index(
        "ix_source_session_lookup", "source_session_metadata", ["market", "ingestion_time"]
    )


def downgrade() -> None:
    for table in (
        "source_session_metadata",
        "suspension_records",
        "share_capital_changes",
        "corporate_actions",
        "reality_symbol_mappings",
        "raw_reference_observations",
    ):
        op.drop_table(table)
