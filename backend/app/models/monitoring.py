from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class MonitoringConfig(Base):
    __tablename__ = "monitoring_configs"

    investigation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="MONITORING_DISABLED", nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    max_autonomous_depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    run_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_snapshot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    memory_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="MONITORING_RUNNING", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    previous_snapshot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    current_snapshot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    change_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    decision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class MonitoringSnapshot(Base):
    __tablename__ = "monitoring_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    graph_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(json_type(), nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relationship_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class InvestigationChange(Base):
    __tablename__ = "investigation_changes"
    __table_args__ = (UniqueConstraint("investigation_id", "dedupe_key", name="uq_investigation_change_dedupe"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_runs.id", ondelete="CASCADE"), index=True
    )
    change_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    relationship_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    before_value: Mapped[dict[str, Any] | None] = mapped_column(json_type(), nullable=True)
    after_value: Mapped[dict[str, Any] | None] = mapped_column(json_type(), nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentDecision(Base):
    __tablename__ = "agent_decisions"
    __table_args__ = (UniqueConstraint("investigation_id", "dedupe_key", name="uq_agent_decision_dedupe"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_runs.id", ondelete="CASCADE"), index=True
    )
    trigger_event: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    relationship_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="RECORDED", nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    followup_investigation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
