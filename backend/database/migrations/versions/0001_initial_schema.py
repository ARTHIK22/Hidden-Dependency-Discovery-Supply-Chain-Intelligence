"""Create the initial backend schema.

Revision ID: 0001_initial_schema
Revises:
"""
from alembic import op

from app.core.database import Base
import app.models  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Initial project migration. The current declarative metadata is the source
    # of truth until a normal Alembic autogeneration produces subsequent diffs.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
