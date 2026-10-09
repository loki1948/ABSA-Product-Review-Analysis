"""Application settings, read from environment variables or ``backend/.env``.

Every variable is prefixed with ``ABSA_`` (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.paths import (
    ASPECT_MODEL_DIR,
    BACKEND_DIR,
    DATA_DIR,
    OVERALL_MODEL_DIR,
    SENTIMENT_MODEL_DIR,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ABSA_", env_file=BACKEND_DIR / ".env", extra="ignore"
    )

    app_name: str = "Aspect-Based Sentiment Analysis API"
    log_level: str = "INFO"

    database_url: str = f"sqlite:///{(DATA_DIR / 'absa.db').as_posix()}"

    aspect_model_dir: Path = ASPECT_MODEL_DIR
    sentiment_model_dir: Path = SENTIMENT_MODEL_DIR
    overall_model_dir: Path = OVERALL_MODEL_DIR
    max_length: int = 128
    # Set to false to start the API without the models (frontend work, tests).
    load_models: bool = True

    # Comma-separated list of frontend origins allowed to call the API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
