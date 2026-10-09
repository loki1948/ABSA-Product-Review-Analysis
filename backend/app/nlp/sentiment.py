"""Pipeline stage 5: sentiment classification (per aspect and overall)."""

from __future__ import annotations

from app.models.sentiment_model import SentimentClassifier, SentimentPrediction
from app.nlp.aspect_extraction import ExtractedAspect
from app.nlp.labels import SENTIMENT_LABELS
from app.nlp.preprocessing import Sentence


def classify_aspects(
    classifier: SentimentClassifier, aspects: list[ExtractedAspect]
) -> list[SentimentPrediction]:
    """Sentiment towards each aspect, judged within the sentence it occurs in.

    Each aspect is paired with its sentence as ``[CLS] sentence [SEP] aspect [SEP]``.
    The whole sentence (not just the nearby clause) is given to BERT so that it
    can resolve things like negation or a comparison that sits in another clause.
    """
    if not aspects:
        return []
    return classifier.predict([a.sentence for a in aspects], [a.text for a in aspects])


def classify_overall(
    classifier: SentimentClassifier, sentences: list[Sentence]
) -> SentimentPrediction:
    """Traditional review-level sentiment, ignoring aspects.

    ``classifier`` is the whole-sentence model (``models/overall_sentiment``).
    It was trained on single sentences, so each sentence is classified on its
    own and the class probabilities are averaged over the review. This also
    avoids truncating long reviews.
    """
    if not sentences:
        return SentimentPrediction("neutral", 0.0, {label: 0.0 for label in SENTIMENT_LABELS})
    predictions = classifier.predict([sentence.text for sentence in sentences])
    probabilities = {
        label: sum(p.probabilities[label] for p in predictions) / len(predictions)
        for label in SENTIMENT_LABELS
    }
    label = max(probabilities, key=probabilities.__getitem__)
    return SentimentPrediction(label, probabilities[label], probabilities)
