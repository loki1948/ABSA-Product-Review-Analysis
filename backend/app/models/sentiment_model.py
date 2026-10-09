"""BERT sequence classifier, used for aspect-level sentiment and for overall sentiment.

The same class wraps two separately trained models: the aspect-sentiment model
(``models/sentiment``, always called with an aspect) and the overall-sentiment
model (``models/overall_sentiment``, always called without one).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.models.batching import Feature, predict_logits
from app.nlp.labels import SENTIMENT_ID2LABEL, SENTIMENT_LABELS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SentimentPrediction:
    label: str
    confidence: float
    probabilities: dict[str, float]


def encode_pair(tokenizer: Any, text: str, aspect: str | None, max_length: int) -> Feature:
    """Encode one classifier input.

    * With an aspect  -> ``[CLS] sentence [SEP] aspect [SEP]``
      BERT's sentence-pair format. Self-attention lets the aspect in the second
      segment attend to the opinion words about it in the first segment, so the
      same sentence can get different labels for different aspects.
    * Without an aspect -> ``[CLS] text [SEP]``
      Ordinary whole-text sentiment classification ("traditional" sentiment).
    """
    if aspect is None:
        encoding = tokenizer(text, truncation=True, max_length=max_length)
    else:
        # only_first: if the pair is too long, shorten the sentence, never the aspect.
        encoding = tokenizer(text, aspect, truncation="only_first", max_length=max_length)
    feature: Feature = {
        "input_ids": encoding["input_ids"],
        "attention_mask": encoding["attention_mask"],
    }
    if "token_type_ids" in encoding:
        feature["token_type_ids"] = encoding["token_type_ids"]
    return feature


class SentimentClassifier:
    """Inference wrapper around a fine-tuned BERT sequence-classification model."""

    def __init__(
        self,
        model: torch.nn.Module,
        tokenizer: Any,
        max_length: int = 128,
        device: torch.device | None = None,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.device = device or torch.device("cpu")
        self.model.to(self.device)

    @classmethod
    def from_pretrained(
        cls, model_dir: Path | str, max_length: int = 128, device: torch.device | None = None
    ) -> "SentimentClassifier":
        logger.info("Loading sentiment model from %s", model_dir)
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
        return cls(model, tokenizer, max_length, device)

    def predict(
        self, texts: list[str], aspects: list[str | None] | None = None, batch_size: int = 32
    ) -> list[SentimentPrediction]:
        """Classify each text, optionally with respect to an aspect.

        ``aspects[i]`` is the aspect for ``texts[i]``; ``None`` (or omitting
        ``aspects``) asks for the sentiment of the text as a whole.
        """
        if aspects is None:
            aspects = [None] * len(texts)
        if len(aspects) != len(texts):
            raise ValueError("texts and aspects must have the same length")
        features = [
            encode_pair(self.tokenizer, text, aspect, self.max_length)
            for text, aspect in zip(texts, aspects)
        ]
        all_logits = predict_logits(
            self.model, features, self.tokenizer.pad_token_id, batch_size, self.device
        )
        predictions: list[SentimentPrediction] = []
        for logits in all_logits:
            probabilities = logits.softmax(dim=-1)
            best = int(probabilities.argmax())
            predictions.append(
                SentimentPrediction(
                    label=SENTIMENT_ID2LABEL[best],
                    confidence=float(probabilities[best]),
                    probabilities={
                        label: float(probabilities[i]) for i, label in enumerate(SENTIMENT_LABELS)
                    },
                )
            )
        return predictions
