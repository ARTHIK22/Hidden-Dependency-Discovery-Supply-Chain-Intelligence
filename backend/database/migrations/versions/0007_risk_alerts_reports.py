"""Add calculated risk snapshots, owned watchlists, alert receipts, and report data.

Revision ID: 0007_risk_alerts_reports
Revises: 0006_verification_ownership
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision = "0007_risk_alerts_reports"
down_revision = "0006_verification_ownership"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    return any(index["name"] == name for index in inspect(op.get_bind()).get_indexes(table))


def _has_fk(table: str, column: str, target: str) -> bool:
    return any(
        foreign_key.get("constrained_columns") == [column]
        and foreign_key.get("referred_table") == target
        for foreign_key in inspect(op.get_bind()).get_foreign_keys(table)
    )


def _json_type() -> sa.TypeEngine:
    return sa.JSON().with_variant(JSONB, "postgresql")


def _add_column(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def _add_fk(table: str, name: str, column: str, referred_table: str, ondelete: str) -> None:
    if not _has_fk(table, column, referred_table):
        op.create_foreign_key(name, table, referred_table, [column], ["id"], ondelete=ondelete)


def _add_index(table: str, name: str, columns: list[str]) -> None:
    if not _has_index(table, name):
        op.create_index(name, table, columns)


def _fill_json(table: str, column: str, value: str) -> None:
    if _has_column(table, column):
        op.execute(sa.text(f"UPDATE {table} SET {column} = '{value}' WHERE {column} IS NULL"))
        op.alter_column(table, column, existing_type=_json_type(), nullable=False)


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    investigation_columns = {column["name"] for column in inspector.get_columns("investigations")}
    _add_column("investigations", sa.Column("risk_progress", _json_type(), nullable=True))
    _add_column("investigations", sa.Column("risk_analysis", _json_type(), nullable=True))
    _add_column("investigations", sa.Column("lifecycle_events", _json_type(), nullable=True))
    if "lifecycle_events" not in investigation_columns:
        _fill_json("investigations", "lifecycle_events", "[]")

    _add_column("risks", sa.Column("score_scale", sa.String(length=16), nullable=True))
    if _has_column("risks", "score_scale"):
        op.execute(sa.text("UPDATE risks SET score_scale = 'fraction' WHERE score_scale IS NULL"))
        op.alter_column("risks", "score_scale", existing_type=sa.String(length=16), nullable=False)
    op.alter_column("risks", "score", existing_type=sa.Float(), nullable=True)
    _add_column("risks", sa.Column("relationship_id", sa.Uuid(), nullable=True))
    _add_column("risks", sa.Column("snapshot_id", sa.Uuid(), nullable=True))
    _add_column("risks", sa.Column("local_score", sa.Float(), nullable=True))
    _add_column("risks", sa.Column("propagated_score", sa.Float(), nullable=True))
    _add_column("risks", sa.Column("risk_factors", _json_type(), nullable=True))
    _fill_json("risks", "risk_factors", "[]")
    _add_fk("risks", "fk_risks_relationship_id_relationships", "relationship_id", "relationships", "SET NULL")
    _add_index("risks", "ix_risks_relationship_id", ["relationship_id"])
    _add_index("risks", "ix_risks_snapshot_id", ["snapshot_id"])

    alert_columns = {column["name"] for column in inspector.get_columns("alerts")}
    _add_column("alerts", sa.Column("relationship_id", sa.Uuid(), nullable=True))
    _add_column("alerts", sa.Column("owner_id", sa.Uuid(), nullable=True))
    _add_column("alerts", sa.Column("dedupe_key", sa.String(length=180), nullable=True))
    _add_column("alerts", sa.Column("reason", sa.Text(), nullable=True))
    _add_column("alerts", sa.Column("risk_score", sa.Float(), nullable=True))
    _add_column("alerts", sa.Column("evidence_ids", _json_type(), nullable=True))
    _add_column("alerts", sa.Column("risk_snapshot", _json_type(), nullable=True))
    if "owner_id" not in alert_columns:
        op.execute(sa.text(
            "UPDATE alerts AS a SET owner_id = i.owner_id "
            "FROM investigations AS i WHERE a.investigation_id = i.id "
            "AND a.owner_id IS NULL AND i.owner_id IS NOT NULL AND i.demo_mode IS DISTINCT FROM TRUE"
        ))
    _fill_json("alerts", "evidence_ids", "[]")
    _add_fk("alerts", "fk_alerts_relationship_id_relationships", "relationship_id", "relationships", "SET NULL")
    _add_fk("alerts", "fk_alerts_owner_id_users", "owner_id", "users", "SET NULL")
    _add_index("alerts", "ix_alerts_relationship_id", ["relationship_id"])
    _add_index("alerts", "ix_alerts_owner_id", ["owner_id"])
    unique_alert_keys = {tuple(item.get("column_names") or ()) for item in inspect(op.get_bind()).get_unique_constraints("alerts")}
    if ("investigation_id", "dedupe_key") not in unique_alert_keys:
        op.create_unique_constraint("uq_alert_investigation_dedupe", "alerts", ["investigation_id", "dedupe_key"])

    _add_column("reports", sa.Column("structured_content", _json_type(), nullable=True))

    watchlist_columns = {column["name"] for column in inspector.get_columns("watchlist_entries")}
    _add_column("watchlist_entries", sa.Column("relationship_id", sa.Uuid(), nullable=True))
    _add_column("watchlist_entries", sa.Column("investigation_id", sa.Uuid(), nullable=True))
    _add_column("watchlist_entries", sa.Column("owner_id", sa.Uuid(), nullable=True))
    _add_column("watchlist_entries", sa.Column("target_type", sa.String(length=32), nullable=True))
    _add_column("watchlist_entries", sa.Column("target_id", sa.Uuid(), nullable=True))
    _add_column("watchlist_entries", sa.Column("target_key", sa.String(length=80), nullable=True))
    _add_column("watchlist_entries", sa.Column("risk_threshold", sa.Float(), nullable=True))
    _add_column("watchlist_entries", sa.Column("condition_json", _json_type(), nullable=True))
    _add_column("watchlist_entries", sa.Column("last_observed", _json_type(), nullable=True))
    op.execute(sa.text("UPDATE watchlist_entries SET target_type = 'entity' WHERE target_type IS NULL"))
    op.execute(sa.text("UPDATE watchlist_entries SET target_id = entity_id WHERE target_id IS NULL AND entity_id IS NOT NULL"))
    op.execute(sa.text("UPDATE watchlist_entries SET target_key = 'entity:' || CAST(entity_id AS VARCHAR) WHERE target_key IS NULL AND entity_id IS NOT NULL"))
    op.alter_column("watchlist_entries", "target_type", existing_type=sa.String(length=32), nullable=False)
    _fill_json("watchlist_entries", "condition_json", "{}")
    _fill_json("watchlist_entries", "last_observed", "{}")
    if "entity_id" in watchlist_columns:
        op.alter_column("watchlist_entries", "entity_id", existing_type=sa.Uuid(), nullable=True)
    for unique in inspect(op.get_bind()).get_unique_constraints("watchlist_entries"):
        if set(unique.get("column_names") or []) == {"entity_id"} and unique.get("name"):
            op.drop_constraint(unique["name"], "watchlist_entries", type_="unique")
    watchlist_uniques = {tuple(item.get("column_names") or ()) for item in inspect(op.get_bind()).get_unique_constraints("watchlist_entries")}
    if ("owner_id", "target_key") not in watchlist_uniques:
        op.create_unique_constraint("uq_watchlist_owner_target", "watchlist_entries", ["owner_id", "target_key"])
    _add_fk("watchlist_entries", "fk_watchlist_relationship_id_relationships", "relationship_id", "relationships", "CASCADE")
    _add_fk("watchlist_entries", "fk_watchlist_investigation_id_investigations", "investigation_id", "investigations", "CASCADE")
    _add_fk("watchlist_entries", "fk_watchlist_owner_id_users", "owner_id", "users", "CASCADE")
    _add_index("watchlist_entries", "ix_watchlist_entries_owner_id", ["owner_id"])
    _add_index("watchlist_entries", "ix_watchlist_entries_relationship_id", ["relationship_id"])
    _add_index("watchlist_entries", "ix_watchlist_entries_investigation_id", ["investigation_id"])

    if "alert_receipts" not in set(inspect(op.get_bind()).get_table_names()):
        op.create_table(
            "alert_receipts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("alert_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], name="fk_alert_receipts_alert_id_alerts", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_alert_receipts_user_id_users", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("alert_id", "user_id", name="uq_alert_receipt_user"),
        )
        op.create_index("ix_alert_receipts_alert_id", "alert_receipts", ["alert_id"])
        op.create_index("ix_alert_receipts_user_id", "alert_receipts", ["user_id"])


def downgrade() -> None:
    raise RuntimeError("This migration is additive and intentionally has no automatic data-dropping downgrade")
