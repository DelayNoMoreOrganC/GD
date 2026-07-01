"""Application configuration via environment variables / pydantic-settings."""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root: this file lives at web/backend/app/config.py
BACKEND_DIR = Path(__file__).resolve().parent.parent          # web/backend
WEB_DIR = BACKEND_DIR.parent                                   # web
PROJECT_ROOT = WEB_DIR.parent                                  # F:\GD
DATA_DIR = WEB_DIR / "data"
DB_PATH = DATA_DIR / "archive.db"
ORGS_DIR = DATA_DIR / "orgs"
FRONTEND_DIST = WEB_DIR / "frontend" / "dist"

V4_ROOT = str(WEB_DIR.parent)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=WEB_DIR / ".env",
        env_prefix="V5_",
        extra="ignore",
    )

    # JWT
    secret_key: str = "change-me-in-production-please"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # File upload limits
    max_upload_mb: int = 200

    # Database
    database_url: str = ""

    # Bootstrap admin (created on first run if no users exist)
    bootstrap_admin_user: str = "admin"
    bootstrap_admin_password: str = "admin123"

    @property
    def sqlite_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"


@lru_cache
def get_settings() -> "Settings":
    s = Settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ORGS_DIR.mkdir(parents=True, exist_ok=True)
    return s
