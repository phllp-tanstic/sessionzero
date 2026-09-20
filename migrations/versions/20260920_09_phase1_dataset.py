"""Immutable native session targets and reproducible Phase 1 dataset linkage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260920_09"
down_revision = "20260919_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "native_session_targets",
        sa.Column("target_version", sa.String(64), primary_key=True),
        *[
            sa.Column(n, sa.String(64), nullable=False)
            for n in (
                "cohort_version",
                "native_ticker",
                "source",
                "calendar_version",
                "transformation_version",
                "target_definition_version",
            )
        ],
        *[sa.Column(n, sa.String(32), nullable=False) for n in ("feed", "adjustment", "status")],
        sa.Column("session_date", sa.Date(), nullable=False),
        *[
            sa.Column(n, sa.DateTime(timezone=True), nullable=False)
            for n in ("regular_open", "regular_close", "ingestion_time")
        ],
        *[
            sa.Column(n, sa.DateTime(timezone=True))
            for n in ("open_observation_time", "close_observation_time")
        ],
        *[sa.Column(n, sa.Numeric()) for n in ("open_target", "close_target")],
        *[
            sa.Column(
                n,
                sa.BigInteger(),
                sa.ForeignKey("raw_native_equity_observations.id", ondelete="RESTRICT"),
            )
            for n in ("open_raw_id", "close_raw_id")
        ],
        *[
            sa.Column(
                n,
                sa.BigInteger(),
                sa.ForeignKey("normalized_native_equity_candles.id", ondelete="RESTRICT"),
            )
            for n in ("open_candle_id", "close_candle_id")
        ],
        *[
            sa.Column(
                n,
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("ingestion_runs.run_id", ondelete="RESTRICT"),
            )
            for n in ("open_run_id", "close_run_id")
        ],
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "status IN ('TARGET_AVAILABLE','OPEN_MISSING','CLOSE_MISSING','BOTH_MISSING',"
            "'PROVIDER_FAILURE','STRUCTURAL_FAILURE','UNKNOWN')",
            name="ck_session_target_status",
        ),
        sa.CheckConstraint("adjustment = 'raw'", name="ck_session_target_raw"),
        sa.CheckConstraint("regular_close > regular_open", name="ck_session_target_bounds"),
        sa.UniqueConstraint(
            "cohort_version",
            "native_ticker",
            "session_date",
            "target_version",
            name="uq_session_target_version",
        ),
    )
    op.create_table(
        "phase1_dataset_manifests",
        sa.Column("dataset_version", sa.String(64), primary_key=True),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "phase1_dataset_targets",
        sa.Column(
            "dataset_version",
            sa.String(64),
            sa.ForeignKey("phase1_dataset_manifests.dataset_version", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("reality_symbol", sa.String(64), primary_key=True),
        sa.Column("session_date", sa.Date(), primary_key=True),
        sa.Column(
            "target_version",
            sa.String(64),
            sa.ForeignKey("native_session_targets.target_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("session_role", sa.String(32), nullable=False),
    )
    op.create_table(
        "phase1_dataset_reality",
        sa.Column(
            "dataset_version",
            sa.String(64),
            sa.ForeignKey("phase1_dataset_manifests.dataset_version", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "candle_id",
            sa.BigInteger(),
            sa.ForeignKey("normalized_market_candles.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "raw_observation_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_market_observations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *[
            sa.Column(n, sa.String(64), nullable=False)
            for n in ("native_ticker", "calendar_version", "previous_close_role", "reality_role")
        ],
        sa.Column("decision_time", sa.DateTime(timezone=True), nullable=False),
        *[
            sa.Column(
                n,
                sa.String(64),
                sa.ForeignKey("native_session_targets.target_version", ondelete="RESTRICT"),
                nullable=False,
            )
            for n in ("previous_close_target_version", "next_open_target_version")
        ],
        sa.Column("next_open_role", sa.String(32), nullable=False),
        sa.CheckConstraint("next_open_role = 'FUTURE_OUTCOME'", name="ck_dataset_future_outcome"),
    )


def downgrade() -> None:
    for table in (
        "phase1_dataset_reality",
        "phase1_dataset_targets",
        "phase1_dataset_manifests",
        "native_session_targets",
    ):
        op.drop_table(table)
