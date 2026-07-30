"""Configuration settings for OSWG."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _xdg_data_home() -> Path:
    """Get XDG data home directory (~/.local/share by default)."""
    env = os.environ.get("XDG_DATA_HOME")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="OSWG_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "OSWG"
    app_version: str = "0.1.0"
    debug: bool = False

    api_prefix: str = "/api/v1"

    data_dir: Path = _xdg_data_home() / "oswg"
    file_storage_path: Path = _xdg_data_home() / "oswg"
    database_path: Path = _xdg_data_home() / "oswg" / "oswg.db"
    default_retention_seconds: int = 3600
    cleanup_interval_seconds: int = 300

    max_pages_default: int = 10
    max_pages_limit: int = 100

    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
