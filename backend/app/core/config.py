from functools import lru_cache
import json
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Hidden Dependency Intelligence"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str | None = None
    redis_url: str | None = None
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    demo_mode: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"
    monitoring_scheduler_enabled: bool = False
    monitoring_scheduler_tick_seconds: int = Field(default=60, ge=30, le=3600)
    monitoring_default_interval_minutes: int = Field(default=60, ge=15, le=10080)
    monitoring_min_interval_minutes: int = Field(default=15, ge=15, le=10080)
    monitoring_max_interval_minutes: int = Field(default=10080, ge=15, le=10080)
    monitoring_evidence_freshness_days: int = Field(default=180, ge=1, le=3650)

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return value

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def allowed_origins(self) -> list[str]:
        value = self.cors_origins.strip()
        if value.startswith("["):
            try:
                decoded = json.loads(value)
                if isinstance(decoded, list):
                    return [str(origin).strip().rstrip("/") for origin in decoded if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [
            origin.strip().rstrip("/")
            for origin in value.split(",")
            if origin.strip()
        ]

    @property
    def development_demo_mode(self) -> bool:
        return self.demo_mode and self.app_env.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
