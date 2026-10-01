from datetime import datetime, timezone
from uuid import UUID, uuid4

from typing import Any
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base, json_type


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Legacy report metadata is retained for deployed database compatibility.
    report_type: Mapped[str] = mapped_column(String(100), default="summary")
    status: Mapped[str] = mapped_column(String(50), default="generated")
