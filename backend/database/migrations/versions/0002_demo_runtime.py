"""Align the deployed PostgreSQL baseline with the active API models.

Revision ID: 0002_demo_runtime
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base
import app.models  # noqa: F401 - register active tables


revision = "0002_demo_runtime"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _columns(bind, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def _add_missing_columns(bind) -> None:
    definitions = {
        "alerts": [
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        ],
        "entities": [
            sa.Column("investigation_id", UUID(as_uuid=True), nullable=True),
            sa.Column("jurisdiction", sa.String(160), nullable=True),
            sa.Column("risk_score", sa.Float(), nullable=True),
            sa.Column("risk_level", sa.String(32), nullable=True),
        ],
        "evidence": [
            sa.Column("source", sa.String(500), nullable=True, server_default="Source metadata unavailable"),
            sa.Column("source_type", sa.String(120), nullable=True, server_default="unknown"),
            sa.Column("published_date", sa.Date(), nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("excerpt", sa.Text(), nullable=True, server_default=""),
            sa.Column("source_url", sa.String(2000), nullable=True),
        ],
        "investigations": [
            sa.Column("goal", sa.Text(), nullable=True),
            sa.Column("progress", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("scope", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("depth", sa.String(24), nullable=False, server_default="deep"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("demo_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        ],
        "relationships": [
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("evidence_summary", sa.Text(), nullable=True),
            sa.Column("investigation_id", UUID(as_uuid=True), nullable=True),
            sa.Column("source", sa.String(500), nullable=True),
        ],
        "risks": [
            sa.Column("level", sa.String(32), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
        ],
        "users": [
            sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        ],
    }
    tables = set(inspect(bind).get_table_names())
    for table_name, columns in definitions.items():
        if table_name not in tables:
            continue
        present = _columns(bind, table_name)
        for column in columns:
            if column.name not in present:
                op.add_column(table_name, column)
                present.add(column.name)


def _backfill_legacy_columns(bind) -> None:
    statements = (
        ("investigations", {"goal", "description", "target", "name"}, "UPDATE investigations SET goal = COALESCE(NULLIF(description, ''), NULLIF(target, ''), name) WHERE goal IS NULL"),
        ("relationships", {"confidence", "confidence_score"}, "UPDATE relationships SET confidence = confidence_score WHERE confidence IS NULL"),
        ("relationships", {"created_at", "discovered_at", "updated_at"}, "UPDATE relationships SET created_at = COALESCE(discovered_at, updated_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL"),
        ("relationships", {"evidence_summary", "description"}, "UPDATE relationships SET evidence_summary = description WHERE evidence_summary IS NULL"),
        ("entities", {"jurisdiction", "country"}, "UPDATE entities SET jurisdiction = country WHERE jurisdiction IS NULL"),
        ("evidence", {"source", "source_id", "url"}, "UPDATE evidence SET source = COALESCE((SELECT s.name FROM sources AS s WHERE s.id = evidence.source_id), url, 'Source metadata unavailable') WHERE source IS NULL"),
        ("evidence", {"source_type", "evidence_type"}, "UPDATE evidence SET source_type = COALESCE(NULLIF(evidence_type, ''), 'unknown') WHERE source_type IS NULL"),
        ("evidence", {"published_date", "published_at"}, "UPDATE evidence SET published_date = published_at::date WHERE published_date IS NULL AND published_at IS NOT NULL"),
        ("evidence", {"captured_at", "collected_at"}, "UPDATE evidence SET captured_at = COALESCE(collected_at, CURRENT_TIMESTAMP) WHERE captured_at IS NULL"),
        ("evidence", {"confidence", "confidence_score"}, "UPDATE evidence SET confidence = confidence_score WHERE confidence IS NULL"),
        ("evidence", {"excerpt", "content"}, "UPDATE evidence SET excerpt = COALESCE(content, '') WHERE excerpt IS NULL"),
        ("evidence", {"source_url", "url"}, "UPDATE evidence SET source_url = url WHERE source_url IS NULL"),
        ("risks", {"level", "severity"}, "UPDATE risks SET level = COALESCE(NULLIF(severity, ''), 'medium') WHERE level IS NULL"),
        ("risks", {"reason", "description", "title"}, "UPDATE risks SET reason = COALESCE(NULLIF(description, ''), NULLIF(title, ''), 'No legacy assessment reason recorded') WHERE reason IS NULL"),
        ("alerts", {"read_at", "created_at", "is_read"}, "UPDATE alerts SET read_at = created_at WHERE read_at IS NULL AND is_read IS TRUE"),
        ("reports", {"content"}, "UPDATE reports SET content = '' WHERE content IS NULL"),
    )
    table_names = set(inspect(bind).get_table_names())
    for table, required_columns, statement in statements:
        if table in table_names and required_columns <= _columns(bind, table):
            bind.execute(text(statement))


def _set_not_null(bind, table: str, column: str, column_type) -> None:
    current = next(item for item in inspect(bind).get_columns(table) if item["name"] == column)
    if current["nullable"]:
        null_count = bind.execute(text(f'SELECT count(*) FROM "{table}" WHERE "{column}" IS NULL')).scalar_one()
        if null_count:
            raise RuntimeError(f"Cannot make {table}.{column} required: {null_count} existing rows are null")
        op.alter_column(table, column, existing_type=column_type, nullable=False)


def _add_investigation_foreign_keys(bind) -> None:
    expected = (
        ("entities", "investigation_id", "fk_entities_investigation_id"),
        ("relationships", "investigation_id", "fk_relationships_investigation_id"),
    )
    inspector = inspect(bind)
    for table, column, name in expected:
        foreign_keys = inspector.get_foreign_keys(table)
        if any(fk.get("constrained_columns") == [column] and fk.get("referred_table") == "investigations" for fk in foreign_keys):
            continue
        op.create_foreign_key(name, table, "investigations", [column], ["id"], ondelete="SET NULL")


def _add_missing_indexes(bind) -> None:
    inspector = inspect(bind)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        present = {index["name"] for index in inspect(bind).get_indexes(table.name)}
        present.update(
            constraint.get("name")
            for constraint in inspect(bind).get_unique_constraints(table.name)
            if constraint.get("name")
        )
        for index in table.indexes:
            if index.name and index.name not in present:
                index.create(bind=bind, checkfirst=True)
                present.add(index.name)


def upgrade() -> None:
    bind = op.get_bind()

    # This creates active application tables on a new database. Existing
    # legacy tables are left in place and reconciled additively below.
    Base.metadata.create_all(bind=bind, checkfirst=True)
    _add_missing_columns(bind)
    _backfill_legacy_columns(bind)

    _set_not_null(bind, "investigations", "goal", sa.Text())
    _set_not_null(bind, "relationships", "created_at", sa.DateTime(timezone=True))
    _set_not_null(bind, "evidence", "source", sa.String(500))
    _set_not_null(bind, "evidence", "source_type", sa.String(120))
    _set_not_null(bind, "evidence", "captured_at", sa.DateTime(timezone=True))
    _set_not_null(bind, "evidence", "excerpt", sa.Text())
    _set_not_null(bind, "risks", "entity_id", UUID(as_uuid=True))
    _set_not_null(bind, "risks", "level", sa.String(32))
    _set_not_null(bind, "risks", "reason", sa.Text())
    _set_not_null(bind, "reports", "content", sa.Text())

    _add_investigation_foreign_keys(bind)
    _add_missing_indexes(bind)


def downgrade() -> None:
    raise RuntimeError("This migration is additive and intentionally has no automatic data-dropping downgrade")
