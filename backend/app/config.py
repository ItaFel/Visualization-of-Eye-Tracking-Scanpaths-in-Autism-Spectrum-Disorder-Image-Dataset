"""Application configuration module."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized runtime settings."""

    app_name: str = "Eye Tracking Autism Diagnosis"
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = 60
    database_url: str = Field(default="sqlite:///backend/app/storage/app.db")
    media_root: Path = Path("backend/app/storage")
    uploads_dir: Path = Path("backend/app/storage/uploads")
    results_dir: Path = Path("backend/app/storage/results")
    model_module: str = Field(
        default="model.scanpath_classifier", validation_alias="MODEL_MODULE"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_directories(self) -> None:
        """Make sure critical directories exist before runtime."""
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
