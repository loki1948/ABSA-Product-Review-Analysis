from __future__ import annotations

import pytest

from app.models.sentiment_model import SentimentPrediction
from app.nlp.labels import SENTIMENT_LABELS
from app.nlp.preprocessing import Sentence
from app.nlp.sentiment import classify_aspects, classify_overall
from tests.conftest import requires_models


class FixedClassifier:
    """Returns prepared probability vectors, in order."""

    def __init__(self, rows: list[tuple[float, float, float]]) -> None:
        self.rows = rows

    def predict(self, texts, aspects=None, batch_size=32) -> list[SentimentPrediction]:
        out = []
        for row in self.rows[: len(texts)]:
            probabilities = dict(zip(SENTIMENT_LABELS, row))
            label = max(probabilities, key=probabilities.__getitem__)
            out.append(SentimentPrediction(label, probabilities[label], probabilities))
        return out


def _sentences(n: int) -> list[Sentence]:
    return [Sentence(f"s{i}", i, i + 2) for i in range(n)]


def test_overall_sentiment_averages_sentence_probabilities() -> None:
    # (negative, neutral, positive) for two sentences
    classifier = FixedClassifier([(0.9, 0.05, 0.05), (0.3, 0.1, 0.6)])
    overall = classify_overall(classifier, _sentences(2))  # type: ignore[arg-type]
    assert overall.label == "negative"
    assert overall.confidence == pytest.approx(0.6)
    assert sum(overall.probabilities.values()) == pytest.approx(1.0)


def test_overall_sentiment_of_empty_review_is_neutral() -> None:
    overall = classify_overall(FixedClassifier([]), [])  # type: ignore[arg-type]
    assert (overall.label, overall.confidence) == ("neutral", 0.0)


def test_classify_aspects_with_no_aspects() -> None:
    assert classify_aspects(FixedClassifier([]), []) == []  # type: ignore[arg-type]


@pytest.mark.model
@requires_models
def test_model_output_is_a_probability_distribution(real_pipeline) -> None:
    prediction = real_pipeline.classifier.predict(["The screen is gorgeous."], ["screen"])[0]
    assert prediction.label in SENTIMENT_LABELS
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-4)
    assert prediction.confidence == pytest.approx(max(prediction.probabilities.values()))


@pytest.mark.model
@requires_models
def test_model_separates_aspects_of_one_sentence(real_pipeline) -> None:
    """The point of ABSA: same sentence, different aspect, different sentiment."""
    sentence = "The screen is gorgeous but the battery life is terrible."
    screen, battery = real_pipeline.classifier.predict([sentence, sentence], ["screen", "battery life"])
    assert screen.label == "positive"
    assert battery.label == "negative"


@pytest.mark.model
@requires_models
def test_model_rejects_mismatched_inputs(real_pipeline) -> None:
    with pytest.raises(ValueError):
        real_pipeline.classifier.predict(["a", "b"], ["x"])
