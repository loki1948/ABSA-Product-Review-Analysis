"""End-to-end ABSA pipeline: review text in, aspect-sentiment map out.

    review
      -> clean_text            (preprocessing)
      -> split_sentences       (preprocessing)
      -> extract_aspects       (BERT token classifier + context identification)
      -> classify_aspects      (BERT sequence classifier, sentence/aspect pairs)
      -> classify_overall      (separate BERT classifier, whole sentences)
      -> AnalysisResult
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.models.aspect_model import AspectExtractor
from app.models.sentiment_model import SentimentClassifier
from app.nlp.aspect_extraction import extract_aspects
from app.nlp.preprocessing import clean_text, split_sentences
from app.nlp.sentiment import classify_aspects, classify_overall

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AspectSentimentResult:
    aspect: str
    sentiment: str
    confidence: float  # probability of the predicted sentiment class
    context: str
    start: int  # character offsets of the aspect in AnalysisResult.review
    end: int
    extraction_confidence: float  # mean tag probability of the aspect's tokens


@dataclass(frozen=True)
class AnalysisResult:
    review: str  # the cleaned text that was analysed
    overall_sentiment: str
    overall_confidence: float
    aspects: list[AspectSentimentResult] = field(default_factory=list)


class ABSAPipeline:
    """Combines the fine-tuned BERT models into one ``analyze`` call.

    ``extractor`` and ``classifier`` are the two ABSA stages. ``overall_classifier``
    is the traditional whole-text sentiment model that the ABSA result is
    compared against; if it is not given, ``classifier`` is used for that too.
    """

    def __init__(
        self,
        extractor: AspectExtractor,
        classifier: SentimentClassifier,
        overall_classifier: SentimentClassifier | None = None,
    ) -> None:
        self.extractor = extractor
        self.classifier = classifier
        self.overall_classifier = overall_classifier or classifier

    @classmethod
    def from_pretrained(
        cls,
        aspect_model_dir: Path | str,
        sentiment_model_dir: Path | str,
        overall_model_dir: Path | str,
        max_length: int = 128,
    ) -> "ABSAPipeline":
        for model_dir in (aspect_model_dir, sentiment_model_dir, overall_model_dir):
            if not (Path(model_dir) / "config.json").exists():
                raise FileNotFoundError(
                    f"No trained model in {model_dir}. Train it first: see README, 'Train the models'."
                )
        return cls(
            AspectExtractor.from_pretrained(aspect_model_dir, max_length),
            SentimentClassifier.from_pretrained(sentiment_model_dir, max_length),
            SentimentClassifier.from_pretrained(overall_model_dir, max_length),
        )

    def analyze(self, review: str) -> AnalysisResult:
        started = time.perf_counter()
        text = clean_text(review)
        sentences = split_sentences(text)

        aspects = extract_aspects(self.extractor, text, sentences)
        sentiments = classify_aspects(self.classifier, aspects)
        overall = classify_overall(self.overall_classifier, sentences)

        result = AnalysisResult(
            review=text,
            overall_sentiment=overall.label,
            overall_confidence=overall.confidence,
            aspects=[
                AspectSentimentResult(
                    aspect=aspect.text,
                    sentiment=sentiment.label,
                    confidence=sentiment.confidence,
                    context=aspect.context,
                    start=aspect.start,
                    end=aspect.end,
                    extraction_confidence=aspect.confidence,
                )
                for aspect, sentiment in zip(aspects, sentiments)
            ],
        )
        logger.info(
            "Analysed review: %d chars, %d sentences, %d aspects, overall=%s, %.0f ms",
            len(text), len(sentences), len(result.aspects), result.overall_sentiment,
            (time.perf_counter() - started) * 1000,
        )
        return result
