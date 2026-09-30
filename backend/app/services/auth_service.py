from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def register_user(db: Session, email: str, password: str, full_name: str) -> User:
    normalized_email = email.strip().lower()
    if db.scalar(select(User).where(User.email == normalized_email)):
        raise ValueError("Email is already registered")
    user = User(email=normalized_email, password_hash=hash_password(password), full_name=full_name.strip(), role="analyst")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user
