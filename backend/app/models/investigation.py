from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
	pass


class Investigation(Base):
	__tablename__ = "investigations"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	goal: Mapped[str] = mapped_column(Text, nullable=False)
	status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
	depth: Mapped[str] = mapped_column(String(30), default="deep", nullable=False)
	scope_manufacturers: Mapped[bool] = mapped_column(Boolean, default=True)
	scope_materials: Mapped[bool] = mapped_column(Boolean, default=True)
	scope_geography: Mapped[bool] = mapped_column(Boolean, default=True)
	scope_verification: Mapped[bool] = mapped_column(Boolean, default=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
