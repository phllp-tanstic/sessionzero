"""Versioned provider-neutral native equity observations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260919_08"
down_revision = "20260914_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_native_equity_observations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_runs.run_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("page_index", sa.Integer(), nullable=False),
        *[
            sa.Column(name, sa.String(64), nullable=False)
            for name in (
                "source",
                "native_ticker",
                "reality_symbol",
                "universe_version",
                "cohort_version",
            )
        ],
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_params", postgresql.JSONB(), nullable=False),
        sa.Column("response_headers", postgresql.JSONB(), nullable=False),
        sa.Column("response_body", sa.String(), nullable=False),
        *[
            sa.Column(name, sa.DateTime(timezone=True), nullable=False)
            for name in ("requested_start", "requested_end", "ingestion_time")
        ],
        sa.UniqueConstraint("run_id", "page_index", name="uq_native_raw_run_page"),
        sa.CheckConstraint("requested_end > requested_start", name="ck_native_raw_bounds"),
    )
    op.create_table(
        "normalized_native_equity_candles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "raw_observation_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_native_equity_observations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *[
            sa.Column(name, sa.String(64), nullable=False)
            for name in ("source", "native_ticker", "content_version", "transformation_version")
        ],
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("feed", sa.String(32), nullable=False),
        sa.Column("adjustment", sa.String(32), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        *[
            sa.Column(name, sa.Numeric(), nullable=False)
            for name in ("open", "high", "low", "close", "volume")
        ],
        sa.Column("trade_count", sa.BigInteger(), nullable=False),
        sa.Column("vwap", sa.Numeric()),
        sa.UniqueConstraint(
            "source",
            "native_ticker",
            "interval",
            "event_time",
            "feed",
            "adjustment",
            "content_version",
            name="uq_native_candle_version",
        ),
        sa.CheckConstraint(
            "low > 0 AND low <= open AND low <= close AND high >= open "
            "AND high >= close AND volume >= 0 AND trade_count >= 0",
            name="ck_native_candle_values",
        ),
        sa.CheckConstraint(
            "interval = '1Min' AND adjustment = 'raw'", name="ck_native_candle_contract"
        ),
    )


def downgrade() -> None:
    op.drop_table("normalized_native_equity_candles")
    op.drop_table("raw_native_equity_observations")
