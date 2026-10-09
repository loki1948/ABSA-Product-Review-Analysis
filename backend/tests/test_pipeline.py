from __future__ import annotations

import pytest

from app.nlp.pipeline import ABSAPipeline
from tests.conftest import requires_models

REVIEW = "The phone has an amazing camera, a bright display, but the battery life is terrible."


def test_pipeline_maps_each_aspect_to_its_sentiment(stub_pipeline: ABSAPipeline) -> None:
    result = stub_pipeline.analyze(REVIEW)
    assert [(a.aspect, a.context) for a in result.aspects] == [
        ("camera", "The phone has an amazing camera"),
        ("display", "a bright display"),
        ("battery life", "the battery life is terrible"),
    ]
    assert result.aspects[-1].sentiment == "negative"
    assert all(result.review[a.start : a.end] == a.aspect for a in result.aspects)


def test_pipeline_cleans_input_and_handles_multiple_sentences(stub_pipeline: ABSAPipeline) -> None:
    result = stub_pipeline.analyze("  Great <b>camera</b>.\n\nThe   screen is bad.  ")
    assert result.review == "Great camera . The screen is bad."
    assert [(a.aspect, a.sentiment) for a in result.aspects] == [
        ("camera", "positive"),
        ("screen", "negative"),
    ]


def test_pipeline_review_without_aspects(stub_pipeline: ABSAPipeline) -> None:
    result = stub_pipeline.analyze("I bought it yesterday.")
    assert result.aspects == []
    assert result.overall_sentiment in {"positive", "negative", "neutral"}


def test_from_pretrained_explains_missing_models(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Train it first"):
        ABSAPipeline.from_pretrained(tmp_path, tmp_path, tmp_path)


@pytest.mark.model
@requires_models
def test_end_to_end_with_trained_models(real_pipeline: ABSAPipeline) -> None:
    result = real_pipeline.analyze(
        "The screen is gorgeous and the keyboard feels great, but the battery life is terrible."
    )
    found = {a.aspect.lower(): a.sentiment for a in result.aspects}
    assert found.get("screen") == "positive"
    assert found.get("battery life") == "negative"
    assert all(0.0 <= a.confidence <= 1.0 for a in result.aspects)
    assert all(result.review[a.start : a.end] == a.aspect for a in result.aspects)
