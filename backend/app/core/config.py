from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BeforeValidator, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def parse_cors_origins(value: Any) -> list[str]:
    if isinstance(value, str):
        if not value:
            return []
        if value.startswith("["):
            import json
            try:
                return list(json.loads(value))
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseBackend(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class StorageBackend(str, Enum):
    LOCAL = "local"
    MINIO = "minio"
    S3 = "s3"
    CLOUDFLARE_R2 = "cloudflare_r2"


class RedisBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"


class SchedulerBackend(str, Enum):
    ASYNC = "async"
    CELERY = "celery"
    DRAMATIQ = "dramatiq"


class NotificationBackend(str, Enum):
    MOCK = "mock"
    FIREBASE = "firebase"
    APNS = "apns"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Signal Clone Backend"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    SECRET_KEY: str = Field(default="dev-secret-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_BACKEND: DatabaseBackend | None = None
    DATABASE_URL: str | None = None
    SQLITE_DATABASE_PATH: str = "./signal_clone.db"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "signal"
    POSTGRES_USER: str = "signal"
    POSTGRES_PASSWORD: str = "signal"
    SQL_ECHO: bool = False

    BACKEND_CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors_origins)] = Field(default_factory=list)

    REDIS_BACKEND: RedisBackend = RedisBackend.MEMORY
    REDIS_URL: str = "redis://localhost:6379/0"

    STORAGE_BACKEND: StorageBackend = StorageBackend.LOCAL
    STORAGE_LOCAL_PATH: str = "./storage"
    STORAGE_PUBLIC_BASE_URL: str = "/api/v1/attachments/download"
    STORAGE_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
    STORAGE_ALLOWED_MIME_TYPES: Annotated[list[str] | str, BeforeValidator(parse_cors_origins)] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/mpeg",
        "video/quicktime",
        "video/webm",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
        "audio/aac",
        "audio/mp4",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]
    S3_BUCKET: str = "signal"
    S3_REGION: str = "auto"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None

    SCHEDULER_BACKEND: SchedulerBackend = SchedulerBackend.ASYNC
    NOTIFICATION_BACKEND: NotificationBackend = NotificationBackend.MOCK


    FIREBASE_PROJECT_ID: str | None = None
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_CREDENTIALS_JSON: str | None = None

    WS_RATE_LIMIT_COUNT: int = 10
    WS_RATE_LIMIT_WINDOW_SECONDS: int = 10
    AUTH_RATE_LIMIT_REGISTER: int = 5
    AUTH_RATE_LIMIT_LOGIN: int = 10
    AUTH_RATE_LIMIT_VERIFY_OTP: int = 5
    AUTH_RATE_LIMIT_REFRESH: int = 30

    HEALTHCHECK_INCLUDE_DETAILS: bool = True

    @computed_field
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        backend = self.DATABASE_BACKEND or (
            DatabaseBackend.SQLITE
            if self.ENVIRONMENT in {Environment.DEVELOPMENT, Environment.TESTING}
            else DatabaseBackend.POSTGRESQL
        )
        if backend == DatabaseBackend.POSTGRESQL:
            return (
                "postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return f"sqlite+aiosqlite:///{self.SQLITE_DATABASE_PATH}"

    @computed_field
    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite", 1)
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        return url

    @computed_field
    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.is_production and self.SECRET_KEY == "dev-secret-key-change-me":
            raise ValueError("SECRET_KEY must be set in production")
        
        if self.is_production:
            if not self.BACKEND_CORS_ORIGINS:
                import logging
                logging.getLogger("uvicorn.error").warning(
                    "BACKEND_CORS_ORIGINS is missing or empty in production. Cross-Origin requests will be blocked."
                )
        else:
            if not self.BACKEND_CORS_ORIGINS:
                self.BACKEND_CORS_ORIGINS = [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ]

        if self.REDIS_BACKEND == RedisBackend.REDIS and not self.REDIS_URL:
            import logging
            logging.getLogger("uvicorn.error").warning(
                "REDIS_URL is not configured. Falling back to in-memory implementation for Redis services."
            )
            self.REDIS_BACKEND = RedisBackend.MEMORY

        return self

    def storage_local_path_resolved(self) -> Path:
        return Path(self.STORAGE_LOCAL_PATH).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
