"""Persist Phase 1 investigation plans.

Revision ID: 0004_investigation_plans
Revises: 0003_alert_investigation_fk
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0004_investigation_plans"
down_revision = "0003_alert_investigation_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("investigations", sa.Column("objective", sa.Text(), nullable=True))
    op.add_column(
        "investigations",
        sa.Column("plan", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
    )
    op.add_column(
        "investigations", sa.Column("planner_mode", sa.String(length=24), nullable=True)
    )


def downgrade() -> None:
    raise RuntimeError("This migration is additive and intentionally has no automatic data-dropping downgrade")