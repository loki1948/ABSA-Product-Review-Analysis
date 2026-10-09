"""Shared test fixtures.

Fast tests use small stand-ins for the BERT models, so the suite runs in
seconds on any machine. Tests marked ``model`` exercise the real trained
models and are skipped automatically while those do not exist yet:

    pytest                  # everything that can run
    pytest -m "not model"   # fast tests only
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.models.aspect_model import TagPrediction
from app.models.sentiment_model import SentimentPrediction
from app.nlp.labels import SENTIMENT_LABELS
from app.nlp.pipeline import ABSAPipeline
from app.nlp.preprocessing import extract_context
from app.paths import ASPECT_MODEL_DIR, OVERALL_MODEL_DIR, SENTIMENT_MODEL_DIR

MODELS_AVAILABLE = all(
    (model_dir / "config.json").exists()
    for model_dir in (ASPECT_MODEL_DIR, SENTIMENT_MODEL_DIR, OVERALL_MODEL_DIR)
)
requires_models = pytest.mark.skipif(not MODELS_AVAILABLE, reason="trained models not found")

NEGATIVE_WORDS = {"terrible", "poor", "bad", "awful"}


class StubExtractor:
    """Tags a fixed set of words as aspects ("battery life" as one two-word aspect)."""

    ASPECT_WORDS = {"camera", "display", "battery", "screen"}

    def predict(self, sentences: list[list[str]], batch_size: int = 32) -> list[list[TagPrediction]]:
        output: list[list[TagPrediction]] = []
        for words in sentences:
            tags: list[TagPrediction] = []
            for i, word in enumerate(words):
                if word.lower() in self.ASPECT_WORDS:
                    tags.append(TagPrediction("B-ASPECT", 0.9))
                elif word.lower() == "life" and i > 0 and words[i - 1].lower() == "battery":
                    tags.append(TagPrediction("I-ASPECT", 0.8))
                else:
                    tags.append(TagPrediction("O", 0.99))
            output.append(tags)
        return output


class StubClassifier:
    """Negative when a negative word is in the aspect's clause (or anywhere, without aspect)."""

    def predict(
        self, texts: list[str], aspects: list[str | None] | None = None, batch_size: int = 32
    ) -> list[SentimentPrediction]:
        aspects = aspects or [None] * len(texts)
        predictions: list[SentimentPrediction] = []
        for text, aspect in zip(texts, aspects):
            scope = text.lower()
            if aspect is not None:
                start = scope.index(aspect.lower())
                scope = extract_context(scope, start, start + len(aspect))
            negative = any(word in scope for word in NEGATIVE_WORDS)
            label = "negative" if negative else "positive"
            probabilities = {name: 0.05 for name in SENTIMENT_LABELS}
            probabilities[label] = 0.9
            predictions.append(SentimentPrediction(label, 0.9, probabilities))
        return predictions


@pytest.fixture
def stub_pipeline() -> ABSAPipeline:
    return ABSAPipeline(StubExtractor(), StubClassifier())  # type: ignore[arg-type]


@pytest.fixture
def client(tmp_path, monkeypatch, stub_pipeline) -> Iterator[TestClient]:
    """API client backed by a temporary database and the stub pipeline."""
    monkeypatch.setenv("ABSA_DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("ABSA_LOAD_MODELS", "false")

    from app.api.deps import get_pipeline
    from app.config import get_settings
    from app.database.database import reset_engine
    from app.main import create_app

    get_settings.cache_clear()
    reset_engine()
    app = create_app()
    app.dependency_overrides[get_pipeline] = lambda: stub_pipeline
    with TestClient(app) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def real_pipeline() -> ABSAPipeline:
    return ABSAPipeline.from_pretrained(ASPECT_MODEL_DIR, SENTIMENT_MODEL_DIR, OVERALL_MODEL_DIR)
