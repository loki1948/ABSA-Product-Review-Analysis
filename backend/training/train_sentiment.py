"""Fine-tune BERT for sentiment classification.

Run from the ``backend`` directory:

    python -m training.train_sentiment --task aspect     # -> models/sentiment
    python -m training.train_sentiment --task overall    # -> models/overall_sentiment

Two separate models are trained with this script:

* ``--task aspect`` (the ABSA model): input ``[CLS] sentence [SEP] aspect [SEP]``,
  label = the gold polarity of that aspect.
* ``--task overall`` (the traditional baseline): input ``[CLS] sentence [SEP]``,
  label = a weak sentence label derived from the sentence's aspect polarities
  (``training.common.sentence_level_label``).

They are kept apart on purpose. A model that is also trained to output the
sentiment of the whole sentence learns to ignore which aspect it was asked
about, which is exactly what aspect-based sentiment analysis must not do.

The best checkpoint by validation macro-F1 is saved.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.models.sentiment_model import SentimentClassifier, encode_pair
from app.nlp.labels import SENTIMENT_ID2LABEL, SENTIMENT_LABEL2ID, SENTIMENT_LABELS
from app.paths import OVERALL_MODEL_DIR, SENTIMENT_MODEL_DIR
from training.common import (
    add_training_args,
    configure_logging,
    fine_tune,
    load_split,
    sentence_level_label,
    set_seed,
    write_training_log,
)
from training.metrics import classification_metrics

Example = tuple[str, str | None, str]  # (text, aspect or None, label)


def aspect_examples(records: list[dict[str, Any]]) -> list[Example]:
    """One example per annotated aspect term; 'conflict' terms are skipped."""
    return [
        (r["text"], a["term"], a["polarity"])
        for r in records
        for a in r["aspects"]
        if a["polarity"] in SENTIMENT_LABEL2ID
    ]


def sentence_examples(records: list[dict[str, Any]]) -> list[Example]:
    """One weakly-labelled whole-sentence example per sentence that has aspects."""
    examples: list[Example] = []
    for r in records:
        label = sentence_level_label([a["polarity"] for a in r["aspects"]])
        if label is not None:
            examples.append((r["text"], None, label))
    return examples


def evaluate_sentiment(classifier: SentimentClassifier, examples: list[Example]) -> dict[str, Any]:
    predictions = classifier.predict([e[0] for e in examples], [e[1] for e in examples])
    return classification_metrics(
        [e[2] for e in examples], [p.label for p in predictions], SENTIMENT_LABELS
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--task", choices=("aspect", "overall"), default="aspect")
    add_training_args(parser, lr=2e-5, epochs=4)
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="default: models/sentiment (aspect) or models/overall_sentiment (overall)")
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = SENTIMENT_MODEL_DIR if args.task == "aspect" else OVERALL_MODEL_DIR
    configure_logging()
    set_seed(args.seed)

    build_examples = aspect_examples if args.task == "aspect" else sentence_examples
    train_examples = build_examples(load_split("train", args.domains, args.limit))
    val_examples = build_examples(load_split("val", args.domains, args.limit))

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    # Pretrained BERT encoder + a new linear layer on the [CLS] representation
    # that outputs the three sentiment classes.
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(SENTIMENT_LABELS),
        id2label=SENTIMENT_ID2LABEL,
        label2id=SENTIMENT_LABEL2ID,
    )
    features = [
        {**encode_pair(tokenizer, text, aspect, args.max_length), "labels": SENTIMENT_LABEL2ID[label]}
        for text, aspect, label in train_examples
    ]
    classifier = SentimentClassifier(model, tokenizer, args.max_length)

    def evaluate() -> dict[str, Any]:
        metrics = evaluate_sentiment(classifier, val_examples)
        return {"accuracy": metrics["accuracy"], "macro_f1": metrics["macro"]["f1"]}

    def save() -> None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)

    result = fine_tune(
        model, features, tokenizer.pad_token_id, args,
        evaluate=evaluate, selection_metric="macro_f1", save=save,
    )
    write_training_log(
        args.output_dir, args, result,
        {"train_examples": len(train_examples), "val_examples": len(val_examples)},
    )


if __name__ == "__main__":
    main()
