"""Stage 1 model: BERT token classifier that tags aspect terms with BIO labels."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from app.models.batching import Feature, predict_logits
from app.nlp.labels import ASPECT_ID2LABEL

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TagPrediction:
    """Predicted BIO tag of one word and the model's probability for it."""

    tag: str
    confidence: float


def encode_words(tokenizer: Any, words: list[str], max_length: int) -> Feature:
    """Encode a pre-tokenised sentence and remember which word each piece came from.

    BERT splits words into word-pieces ("touchpad" -> "touch", "##pad") but our
    BIO labels are per *word*. ``word_ids`` records, for every word-piece, the
    index of its source word (``None`` for [CLS]/[SEP]) so labels and
    predictions can be aligned.
    """
    encoding = tokenizer(words, is_split_into_words=True, truncation=True, max_length=max_length)
    feature: Feature = {
        "input_ids": encoding["input_ids"],
        "attention_mask": encoding["attention_mask"],
        "word_ids": encoding.word_ids(),
    }
    if "token_type_ids" in encoding:
        feature["token_type_ids"] = encoding["token_type_ids"]
    return feature


class AspectExtractor:
    """Inference wrapper around a fine-tuned BERT token-classification model."""

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
    ) -> "AspectExtractor":
        logger.info("Loading aspect-extraction model from %s", model_dir)
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
        return cls(model, tokenizer, max_length, device)

    def predict(self, sentences: list[list[str]], batch_size: int = 32) -> list[list[TagPrediction]]:
        """Tag every word of every pre-tokenised sentence.

        Returns one ``TagPrediction`` per input word. Following the usual BERT
        NER recipe, a word takes the prediction of its *first* word-piece.
        Words cut off by ``max_length`` are tagged ``O``.
        """
        predictions = [[TagPrediction("O", 0.0) for _ in words] for words in sentences]
        todo = [i for i, words in enumerate(sentences) if words]
        features = [encode_words(self.tokenizer, sentences[i], self.max_length) for i in todo]
        model_inputs = [{k: v for k, v in f.items() if k != "word_ids"} for f in features]
        all_logits = predict_logits(
            self.model, model_inputs, self.tokenizer.pad_token_id, batch_size, self.device
        )
        for i, feature, logits in zip(todo, features, all_logits):
            confidences, label_ids = logits.softmax(dim=-1).max(dim=-1)
            previous_word: int | None = None
            for position, word_id in enumerate(feature["word_ids"]):
                if word_id is not None and word_id != previous_word:
                    predictions[i][word_id] = TagPrediction(
                        ASPECT_ID2LABEL[int(label_ids[position])], float(confidences[position])
                    )
                previous_word = word_id
        return predictions
