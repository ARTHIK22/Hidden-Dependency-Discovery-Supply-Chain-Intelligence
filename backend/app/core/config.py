from functools import lru_cache
import secrets
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Hidden Dependency Intelligence"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    DATABASE_URL: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(48)
    )

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()

        if not raw:
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]

        return [
            origin.strip()
            for origin in raw.split(",")
            if origin.strip()
        ]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:

        origins = [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]

        for origin in origins:
            parsed = urlparse(origin)

            if parsed.scheme not in {"http", "https"}:
                raise ValueError(
                    "CORS origins must use http or https"
                )

            if not parsed.netloc:
                raise ValueError(
                    f"Invalid CORS origin: {origin}"
                )

        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
