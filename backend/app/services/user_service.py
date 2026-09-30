from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def list_users(db: Session, limit: int = 100, offset: int = 0) -> list[User]:
    return list(db.scalars(select(User).order_by(User.email).limit(limit).offset(offset)))
