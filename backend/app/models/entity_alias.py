from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (UniqueConstraint("entity_id", "alias", name="uq_entity_alias"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alias: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    alias_type: Mapped[str] = mapped_column(
        String(100),
        default="name",
        nullable=False,
    )
