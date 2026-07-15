"""Application configuration via environment variables / pydantic-settings."""
from __future__ import annotations

import os
import shutil
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


def find_chromium(configured_path: str = "") -> str:
    """Return a usable Chrome/Chromium executable for HTML-to-PDF rendering."""
    candidates = [configured_path]
    if os.name == "nt":
        candidates.extend([
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ])
    elif os.sys.platform == "darwin":
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ])
    for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(command)
        if found:
            candidates.append(found)
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return ""


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
    chromium_path: str = ""

    # Cross-platform document workflow. macOS/Linux default to browser-only
    # preview editing because Word COM is unavailable there. Windows keeps the
    # original DOCX generation/assembly workflow unless explicitly overridden.
    preview_only: bool = os.name != "nt"
    registration_enabled: bool = True

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

    @property
    def capabilities(self) -> dict[str, object]:
        chromium = find_chromium(self.chromium_path)
        return {
            "platform": os.sys.platform,
            "mode": "preview-only" if self.preview_only else "docx",
            "preview_only": self.preview_only,
            "docx_generation": not self.preview_only,
            "archive_assembly": not self.preview_only or bool(chromium),
            "html_pdf_generation": bool(chromium),
            "registration_enabled": self.registration_enabled,
        }

    @property
    def chromium_executable(self) -> str:
        return find_chromium(self.chromium_path)


@lru_cache
def get_settings() -> "Settings":
    s = Settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ORGS_DIR.mkdir(parents=True, exist_ok=True)
    return s
