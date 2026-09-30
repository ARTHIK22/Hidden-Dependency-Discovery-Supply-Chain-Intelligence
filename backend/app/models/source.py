from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (CheckConstraint("reliability_score >= 0 AND reliability_score <= 1", name="ck_source_reliability_range"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    publisher: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reliability_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
