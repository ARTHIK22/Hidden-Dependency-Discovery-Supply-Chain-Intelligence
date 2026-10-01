"""Ensure the optional investigation link on alerts.

Revision ID: 0003_alert_investigation_fk
Revises: 0002_demo_runtime
"""

from alembic import op
from sqlalchemy import inspect


revision = "0003_alert_investigation_fk"
down_revision = "0002_demo_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = inspect(bind).get_foreign_keys("alerts")
    if any(
        fk.get("constrained_columns") == ["investigation_id"]
        and fk.get("referred_table") == "investigations"
        for fk in existing
    ):
        return
    op.create_foreign_key(
        "fk_alerts_investigation_id",
        "alerts",
        "investigations",
        ["investigation_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    raise RuntimeError("This migration is additive and intentionally has no automatic constraint-dropping downgrade")
