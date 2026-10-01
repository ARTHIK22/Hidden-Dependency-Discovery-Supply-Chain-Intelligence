from datetime import datetime, timezone
from uuid import UUID, uuid4

from typing import Any
from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base, json_type


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (UniqueConstraint("owner_id", "target_key", name="uq_watchlist_owner_target"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True)
    relationship_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("relationships.id", ondelete="CASCADE"), nullable=True, index=True)
    investigation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    target_type: Mapped[str] = mapped_column(String(32), default="entity")
    target_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    target_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    risk_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    condition_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    last_observed: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    status: Mapped[str] = mapped_column(String(32), default="watching")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AlertReceipt(Base):
    __tablename__ = "alert_receipts"
    __table_args__ = (UniqueConstraint("alert_id", "user_id", name="uq_alert_receipt_user"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
