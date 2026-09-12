"""Add bounded history quality metadata to ingestion runs.

Revision ID: 20260912_02
Revises: 20260912_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_02"
down_revision: str | None = "20260912_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs", sa.Column("requested_start", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "ingestion_runs", sa.Column("requested_end", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("ingestion_runs", sa.Column("interval", sa.String(length=16), nullable=True))
    op.add_column("ingestion_runs", sa.Column("pages_requested", sa.Integer(), nullable=True))
    op.add_column(
        "ingestion_runs", sa.Column("quality_status", sa.String(length=16), nullable=True)
    )
    op.create_check_constraint(
        "ck_run_pages_requested_positive",
        "ingestion_runs",
        "pages_requested IS NULL OR pages_requested >= 1",
    )
    op.create_check_constraint(
        "ck_run_quality_status",
        "ingestion_runs",
        "quality_status IS NULL OR quality_status IN ('PASS', 'WARN', 'FAIL')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_run_quality_status", "ingestion_runs", type_="check")
    op.drop_constraint("ck_run_pages_requested_positive", "ingestion_runs", type_="check")
    op.drop_column("ingestion_runs", "quality_status")
    op.drop_column("ingestion_runs", "pages_requested")
    op.drop_column("ingestion_runs", "interval")
    op.drop_column("ingestion_runs", "requested_end")
    op.drop_column("ingestion_runs", "requested_start")
