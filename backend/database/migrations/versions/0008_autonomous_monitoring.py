"""Add persisted monitoring, change, and autonomous decision records.

Revision ID: 0008_autonomous_monitoring
Revises: 0007_risk_alerts_reports
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

from app.models.monitoring import AgentDecision, InvestigationChange, MonitoringConfig, MonitoringRun, MonitoringSnapshot


revision = "0008_autonomous_monitoring"
down_revision = "0007_risk_alerts_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    investigation_columns = {item["name"] for item in inspector.get_columns("investigations")}
    if "autonomous_context" not in investigation_columns:
        op.add_column("investigations", sa.Column("autonomous_context", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True))

    for table in (
        MonitoringConfig.__table__,
        MonitoringRun.__table__,
        MonitoringSnapshot.__table__,
        InvestigationChange.__table__,
        AgentDecision.__table__,
    ):
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    raise RuntimeError("This migration is additive and intentionally has no automatic data-dropping downgrade")
