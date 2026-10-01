from datetime import datetime, timezone
from uuid import UUID, uuid4

from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    target_entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    investigation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True, index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="unknown", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Legacy columns remain mapped so new ORM inserts satisfy deployed constraints.
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
