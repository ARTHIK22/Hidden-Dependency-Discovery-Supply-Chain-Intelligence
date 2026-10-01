from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


def json_type():
    """Use JSON on SQLite and JSONB on PostgreSQL, matching forward migrations."""
    return JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass
