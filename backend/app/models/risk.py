from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base, json_type


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    investigation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_scale: Mapped[str] = mapped_column(String(16), default="percent")
    level: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(Text)
    relationship_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("relationships.id", ondelete="SET NULL"), nullable=True, index=True
    )
    snapshot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    local_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    propagated_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[list[dict[str, object]]] = mapped_column(json_type(), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    # Legacy column set remains required by the deployed PostgreSQL schema.
    risk_type: Mapped[str] = mapped_column(String(100), default="dependency")
    severity: Mapped[str] = mapped_column(String(50), default="medium")
    title: Mapped[str] = mapped_column(String(500), default="Risk assessment")
