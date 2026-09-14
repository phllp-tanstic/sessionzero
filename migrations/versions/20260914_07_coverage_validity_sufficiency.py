"""Separate structural validity from duration and availability sufficiency.

Revision ID: 20260914_07
Revises: 20260914_06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_07"
down_revision: str | None = "20260914_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "historical_coverage_members",
        sa.Column("structural_quality_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "historical_coverage_members",
        sa.Column(
            "provider_boundary_spillover_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    for name in (
        "meets_duration_requirement",
        "pre_oos_observation_present",
        "oos_observation_present",
        "final_oos_feasible",
    ):
        op.add_column(
            "historical_coverage_members",
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    for name in ("final_oos_window_start", "final_oos_window_end"):
        op.add_column(
            "historical_coverage_members",
            sa.Column(name, sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    for name in (
        "final_oos_window_end",
        "final_oos_window_start",
        "final_oos_feasible",
        "oos_observation_present",
        "pre_oos_observation_present",
        "meets_duration_requirement",
        "provider_boundary_spillover_count",
        "structural_quality_status",
    ):
        op.drop_column("historical_coverage_members", name)
