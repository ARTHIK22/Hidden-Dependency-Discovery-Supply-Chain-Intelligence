from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    relationship_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("relationships.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(120))
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="needs_review")
    excerpt: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Legacy columns are retained for the existing database contract.
    title: Mapped[str] = mapped_column(String(500), default="Evidence record")
    content: Mapped[str] = mapped_column(Text, default="")
    evidence_type: Mapped[str] = mapped_column(String(100), default="source")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
