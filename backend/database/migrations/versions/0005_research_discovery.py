"""Add Phase 2 research state and evidence investigation provenance.

Revision ID: 0005_research_discovery
Revises: 0004_investigation_plans
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision = "0005_research_discovery"
down_revision = "0004_investigation_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    investigation_columns = {column["name"] for column in inspector.get_columns("investigations")}
    if "research_mode" not in investigation_columns:
        op.add_column("investigations", sa.Column("research_mode", sa.String(length=24), nullable=True))
    if "research_progress" not in investigation_columns:
        op.add_column(
            "investigations",
            sa.Column("research_progress", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
        )

    evidence_columns = {column["name"] for column in inspect(bind).get_columns("evidence")}
    if "investigation_id" not in evidence_columns:
        op.add_column("evidence", sa.Column("investigation_id", sa.Uuid(), nullable=True))

    foreign_keys = inspect(bind).get_foreign_keys("evidence")
    has_investigation_fk = any(
        fk.get("constrained_columns") == ["investigation_id"]
        and fk.get("referred_table") == "investigations"
        for fk in foreign_keys
    )
    if not has_investigation_fk:
        op.create_foreign_key(
            "fk_evidence_investigation_id_investigations",
            "evidence",
            "investigations",
            ["investigation_id"],
            ["id"],
            ondelete="SET NULL",
        )

    indexes = inspect(bind).get_indexes("evidence")
    if not any(index.get("column_names") == ["investigation_id"] for index in indexes):
        op.create_index("ix_evidence_investigation_id", "evidence", ["investigation_id"])


def downgrade() -> None:
    raise RuntimeError(
        "This migration is additive and intentionally has no automatic data-dropping downgrade"
    )
