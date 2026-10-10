"""Fine-tune BERT for aspect-term extraction (token classification, BIO tags).

Run from the ``backend`` directory:

    python -m training.train_aspect

The best checkpoint (by validation span-F1) is saved to ``models/aspect_extraction``.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from transformers import AutoModelForTokenClassification, AutoTokenizer

from app.models.aspect_model import AspectExtractor, encode_words
from app.models.batching import Feature
from app.nlp.labels import ASPECT_ID2LABEL, ASPECT_LABEL2ID, ASPECT_LABELS, IGNORE_INDEX
from app.nlp.preprocessing import bio_to_spans
from app.paths import ASPECT_MODEL_DIR
from training.common import (
    add_training_args,
    refuse_limited_default,
    configure_logging,
    fine_tune,
    load_split,
    set_seed,
    write_training_log,
)
from training.metrics import span_prf


def build_feature(tokenizer: Any, record: dict[str, Any], max_length: int) -> Feature:
    """Turn one sentence into model inputs with word-piece-aligned BIO labels.

    Example for "The touchpad is great" with the aspect "touchpad":

        word-pieces : [CLS]  the  touch     ##pad  is  great  [SEP]
        labels      : -100   O    B-ASPECT  -100   O   O      -100

    Only the first word-piece of a word carries the word's label. Special
    tokens and continuation pieces get IGNORE_INDEX so the loss skips them.
    """
    feature = encode_words(tokenizer, record["tokens"], max_length)
    labels: list[int] = []
    previous_word: int | None = None
    for word_id in feature.pop("word_ids"):
        if word_id is None or word_id == previous_word:
            labels.append(IGNORE_INDEX)
        else:
            labels.append(ASPECT_LABEL2ID[record["tags"][word_id]])
        previous_word = word_id
    feature["labels"] = labels
    return feature


def evaluate_extraction(extractor: AspectExtractor, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Exact-match span precision / recall / F1 of ``extractor`` on ``records``."""
    predictions = extractor.predict([r["tokens"] for r in records])
    gold = [set(bio_to_spans(r["tags"])) for r in records]
    predicted = [set(bio_to_spans([p.tag for p in sentence])) for sentence in predictions]
    return span_prf(gold, predicted)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_training_args(parser, lr=3e-5, epochs=3)
    parser.add_argument("--output-dir", type=Path, default=ASPECT_MODEL_DIR)
    args = parser.parse_args()
    refuse_limited_default(args.limit, args.output_dir, ASPECT_MODEL_DIR, "--output-dir")
    configure_logging()
    set_seed(args.seed)

    train_records = load_split("train", args.domains, args.limit)
    val_records = load_split("val", args.domains, args.limit)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    # Pretrained BERT encoder + a new, randomly initialised linear layer that
    # maps every token's hidden state to the three BIO classes.
    model = AutoModelForTokenClassification.from_pretrained(
        args.model_name,
        num_labels=len(ASPECT_LABELS),
        id2label=ASPECT_ID2LABEL,
        label2id=ASPECT_LABEL2ID,
    )
    features = [build_feature(tokenizer, r, args.max_length) for r in train_records]
    extractor = AspectExtractor(model, tokenizer, args.max_length)

    def save() -> None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)

    result = fine_tune(
        model, features, tokenizer.pad_token_id, args,
        evaluate=lambda: evaluate_extraction(extractor, val_records),
        selection_metric="f1",
        save=save,
    )
    write_training_log(
        args.output_dir, args, result,
        {"train_sentences": len(train_records), "val_sentences": len(val_records)},
    )


if __name__ == "__main__":
    main()
