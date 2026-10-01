"""Baseline for the previously deployed PostgreSQL schema.

Revision ID: 0001_initial_schema
Revises:
"""

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing deployments record this baseline. The next revision adds the
    # active application's schema without dropping legacy tables or records.
    pass


def downgrade() -> None:
    # This baseline owns pre-existing user data and cannot be safely reversed.
    pass
