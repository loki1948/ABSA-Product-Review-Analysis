"""Filesystem locations used across the project."""

from __future__ import annotations

from pathlib import Path

BACKEND_DIR: Path = Path(__file__).resolve().parents[1]
PROJECT_ROOT: Path = BACKEND_DIR.parent

DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"

MODELS_DIR: Path = PROJECT_ROOT / "models"
ASPECT_MODEL_DIR: Path = MODELS_DIR / "aspect_extraction"
SENTIMENT_MODEL_DIR: Path = MODELS_DIR / "sentiment"
OVERALL_MODEL_DIR: Path = MODELS_DIR / "overall_sentiment"

DOCS_DIR: Path = PROJECT_ROOT / "docs"
