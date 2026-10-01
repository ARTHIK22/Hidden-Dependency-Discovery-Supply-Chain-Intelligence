from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import settings
from app.models.user import User


def _signing_key() -> str:
    key = settings.jwt_secret_key.strip()
    if len(key.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")
    return key


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    claims: dict[str, Any] = {
        "sub": str(user.id),
        "ver": user.token_version,
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(claims, _signing_key(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> tuple[UUID, int] | None:
    try:
        claims = jwt.decode(token, _signing_key(), algorithms=[settings.jwt_algorithm])
        user_id = UUID(claims["sub"])
        version = claims.get("ver")
        if isinstance(version, bool) or not isinstance(version, int):
            return None
        return user_id, version
    except (JWTError, KeyError, TypeError, ValueError, RuntimeError):
        return None
