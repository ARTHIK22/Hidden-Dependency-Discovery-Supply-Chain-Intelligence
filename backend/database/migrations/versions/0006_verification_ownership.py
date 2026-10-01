"""Persist verification progress and investigation ownership.

Revision ID: 0006_verification_ownership
Revises: 0005_research_discovery
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision = "0006_verification_ownership"
down_revision = "0005_research_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("investigations")}
    if "verification_mode" not in columns:
        op.add_column("investigations", sa.Column("verification_mode", sa.String(length=24), nullable=True))
    if "verification_progress" not in columns:
        op.add_column(
            "investigations",
            sa.Column("verification_progress", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
        )
    if "owner_id" not in columns:
        op.add_column("investigations", sa.Column("owner_id", sa.Uuid(), nullable=True))
    foreign_keys = inspect(op.get_bind()).get_foreign_keys("investigations")
    if not any(fk.get("constrained_columns") == ["owner_id"] and fk.get("referred_table") == "users" for fk in foreign_keys):
        op.create_foreign_key(
            "fk_investigations_owner_id_users", "investigations", "users", ["owner_id"], ["id"], ondelete="SET NULL"
        )
    indexes = inspect(op.get_bind()).get_indexes("investigations")
    if not any(index.get("column_names") == ["owner_id"] for index in indexes):
        op.create_index("ix_investigations_owner_id", "investigations", ["owner_id"])


def downgrade() -> None:
    raise RuntimeError("This migration is additive and intentionally has no automatic data-dropping downgrade")
