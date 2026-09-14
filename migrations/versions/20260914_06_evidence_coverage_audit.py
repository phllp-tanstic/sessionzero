"""Add evidence-qualified coverage lineage and exact session denominators.

Revision ID: 20260914_06
Revises: 20260913_05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_06"
down_revision: str | None = "20260913_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "historical_coverage_profiles",
        sa.Column(
            "evaluation_scope",
            sa.String(40),
            nullable=False,
            server_default="CANONICAL_SUBSET",
        ),
    )
    for name in (
        "cohort_version",
        "cohort_derivation_version",
        "source_session_evidence_version",
        "git_commit",
    ):
        op.add_column("historical_coverage_profiles", sa.Column(name, sa.String(64), nullable=True))

    count_columns = (
        "expected_open_interval_count",
        "observed_while_expected_open_count",
        "expected_closed_interval_count",
        "observed_while_expected_closed_count",
        "source_session_unknown_interval_count",
        "observed_while_source_session_unknown_count",
        "holiday_ambiguous_interval_count",
    )
    for name in count_columns:
        op.add_column(
            "historical_coverage_members",
            sa.Column(name, sa.Integer(), nullable=False, server_default="0"),
        )
    for name in ("observed_over_known_expected", "missing_over_known_expected"):
        op.add_column(
            "historical_coverage_members", sa.Column(name, sa.Numeric(18, 15), nullable=True)
        )
    op.add_column(
        "historical_coverage_members",
        sa.Column("unknown_fraction", sa.Numeric(18, 15), nullable=False, server_default="0"),
    )
    op.add_column(
        "historical_coverage_members",
        sa.Column("left_censored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "historical_coverage_members",
        sa.Column(
            "holiday_ambiguous_timestamps",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "historical_coverage_members",
        sa.Column(
            "source_session_evidence_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    for name in (
        "source_session_evidence_ids",
        "holiday_ambiguous_timestamps",
        "left_censored",
        "unknown_fraction",
        "missing_over_known_expected",
        "observed_over_known_expected",
        "holiday_ambiguous_interval_count",
        "observed_while_source_session_unknown_count",
        "source_session_unknown_interval_count",
        "observed_while_expected_closed_count",
        "expected_closed_interval_count",
        "observed_while_expected_open_count",
        "expected_open_interval_count",
    ):
        op.drop_column("historical_coverage_members", name)
    for name in (
        "git_commit",
        "source_session_evidence_version",
        "cohort_derivation_version",
        "cohort_version",
        "evaluation_scope",
    ):
        op.drop_column("historical_coverage_profiles", name)
