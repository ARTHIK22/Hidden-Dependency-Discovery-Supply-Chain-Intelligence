from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base, json_type


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("investigation_id", "dedupe_key", name="uq_alert_investigation_dedupe"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True, index=True)
    relationship_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("relationships.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    # Deployed legacy schema requires these older notification attributes.
    alert_type: Mapped[str] = mapped_column(String(100), default="risk")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(json_type(), default=list)
    risk_snapshot: Mapped[dict[str, object] | None] = mapped_column(json_type(), nullable=True)
