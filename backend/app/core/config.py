# backend/app/core/config.py

from functools import lru_cache
import json
import secrets
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Hidden Dependency Intelligence"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "hidden_dependency_intelligence"
    )

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # IMPORTANT:
    # Keep this as a STRING.
    # pydantic-settings otherwise tries to parse list values
    # from .env as JSON before validation.
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        origins = self.cors_origins_list
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or origin == "*":
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        if self.APP_ENV.lower() == "production":
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Accept either a JSON string array or comma-separated origins."""
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("CORS_ORIGINS is not valid JSON") from exc
            if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
                raise ValueError("CORS_ORIGINS JSON must be an array of strings")
            return [origin.strip() for origin in parsed if origin.strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
