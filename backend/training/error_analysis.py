"""Where the deployed models go wrong, and how well they transfer.

Run from the ``backend`` directory, after ``python -m training.evaluate``:

    python -m training.error_analysis

Writes two documents from the models' predictions on the gold test set:

* ``docs/error_analysis.md`` - aspect-extraction errors by type, the aspect
  terms missed most often, sentiment confusions, accuracy by confidence, and a
  fixed sample of misclassified examples.
* ``docs/transfer.md`` - the earlier laptops-only models on restaurant reviews
  (out of domain) against the two-domain models, and the pipeline's output on
  hand-written reviews of other product categories.

Nothing in those files is typed by hand.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.paths import (
    ASPECT_MODEL_DIR,
    DATA_DIR,
    DOCS_DIR,
    MODELS_DIR,
    OVERALL_MODEL_DIR,
    SENTIMENT_MODEL_DIR,
)

logger = logging.getLogger("error_analysis")

Span = tuple[int, int]  # (first_token, last_token_exclusive), as bio_to_spans returns
BANDS = ("below 0.60", "0.60 to 0.80", "0.80 and above")
SAMPLE_SIZE = 20
TOP_MISSED = 15


def _overlap(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def extraction_outcomes(gold: set[Span], predicted: set[Span]) -> dict[str, list[Span]]:
    """Sort one sentence's aspects into the four things that can happen.

    ``correct``  gold aspect predicted with exactly the same boundaries
    ``boundary`` gold aspect that a prediction overlaps without matching it
                 ("battery" predicted for "battery life")
    ``missed``   gold aspect no prediction touches
    ``spurious`` prediction that touches no gold aspect
    """
    outcome: dict[str, list[Span]] = {"correct": [], "boundary": [], "missed": [], "spurious": []}
    for span in sorted(gold):
        if span in predicted:
            outcome["correct"].append(span)
        elif any(_overlap(span, other) for other in predicted):
            outcome["boundary"].append(span)
        else:
            outcome["missed"].append(span)
    for span in sorted(predicted):
        if not any(_overlap(span, other) for other in gold):
            outcome["spurious"].append(span)
    return outcome


def confidence_band(confidence: float) -> str:
    return BANDS[0] if confidence < 0.6 else BANDS[1] if confidence < 0.8 else BANDS[2]


def accuracy_by_band(predictions: list[tuple[float, bool]]) -> list[tuple[str, int, float | None]]:
    """(band, number of predictions, accuracy) from (confidence, was it right) pairs."""
    rows: list[tuple[str, int, float | None]] = []
    for band in BANDS:
        hits = [right for confidence, right in predictions if confidence_band(confidence) == band]
        rows.append((band, len(hits), sum(hits) / len(hits) if hits else None))
    return rows


def _confidence(value: float) -> str:
    """Whole percent; only an exact 1 is shown as 100%, as in the web interface."""
    rounded = round(value * 100)
    return f"{rounded if value >= 1 else min(rounded, 99)}%"


def _share(part: int, whole: int) -> str:
    return f"{part / whole:.1%}" if whole else "n/a"


def analyse_extraction(extractor: Any, records: list[dict[str, Any]]) -> dict[str, Any]:
    from app.nlp.preprocessing import bio_to_spans

    predictions = extractor.predict([r["tokens"] for r in records])
    counts: Counter[str] = Counter()
    missed_terms: Counter[str] = Counter()
    by_length = {"one word": [0, 0], "several words": [0, 0]}  # [found exactly, total]
    for record, tags in zip(records, predictions):
        gold = set(bio_to_spans(record["tags"]))
        outcome = extraction_outcomes(gold, set(bio_to_spans([p.tag for p in tags])))
        for kind, spans in outcome.items():
            counts[kind] += len(spans)
        for first, end in outcome["missed"] + outcome["boundary"]:
            missed_terms[" ".join(record["tokens"][first:end]).lower()] += 1
        for first, end in gold:
            bucket = by_length["one word" if end - first == 1 else "several words"]
            bucket[1] += 1
            bucket[0] += (first, end) in outcome["correct"]
    return {"counts": counts, "missed_terms": missed_terms.most_common(TOP_MISSED), "by_length": by_length}


def analyse_sentiment(classifier: Any, records: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    from training.train_sentiment import aspect_examples

    examples = aspect_examples(records)
    predictions = classifier.predict([e[0] for e in examples], [e[1] for e in examples])
    confusions: Counter[tuple[str, str]] = Counter()
    scored: list[tuple[float, bool]] = []
    wrong: list[tuple[str, str, str, str, float]] = []
    for (text, aspect, gold), prediction in zip(examples, predictions):
        right = prediction.label == gold
        scored.append((prediction.confidence, right))
        if not right:
            confusions[(gold, prediction.label)] += 1
            wrong.append((text, aspect or "", gold, prediction.label, prediction.confidence))
    random.Random(seed).shuffle(wrong)
    return {
        "total": len(examples),
        "errors": len(wrong),
        "confusions": confusions.most_common(),
        "bands": accuracy_by_band(scored),
        "sample": wrong[:SAMPLE_SIZE],
    }


def render_error_analysis(per_domain: dict[str, dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Error analysis",
        "",
        "> Generated by `python -m training.error_analysis`. Do not edit by hand.",
        "",
        f"- Generated: {generated_at}",
        "- Models: the deployed models; data: SemEval-2014 Task 4 gold test set.",
        "- Headline metrics are in [results.md](results.md); this file looks at the errors behind them.",
        "",
    ]
    for domain, analysis in per_domain.items():
        extraction, sentiment = analysis["extraction"], analysis["sentiment"]
        counts = extraction["counts"]
        gold_total = counts["correct"] + counts["boundary"] + counts["missed"]
        lines += [
            f"## Domain: {domain}",
            "",
            "### Aspect extraction",
            "",
            "| Outcome | Aspects | Share of gold aspects |",
            "|---|---|---|",
            f"| Found with exact boundaries | {counts['correct']} | {_share(counts['correct'], gold_total)} |",
            f"| Found with wrong boundaries | {counts['boundary']} | {_share(counts['boundary'], gold_total)} |",
            f"| Missed entirely | {counts['missed']} | {_share(counts['missed'], gold_total)} |",
            "",
            f"Predictions that match no gold aspect (spurious): {counts['spurious']}.",
            "",
            "| Aspect length | Gold aspects | Found exactly |",
            "|---|---|---|",
        ]
        for name, (found, total) in extraction["by_length"].items():
            lines.append(f"| {name} | {total} | {_share(found, total)} |")
        lines += ["", "Aspect terms most often missed or cut short:", ""]
        lines += [f"- {term} ({count})" for term, count in extraction["missed_terms"]] or ["- none"]
        lines += [
            "",
            "### Aspect sentiment (gold aspects given)",
            "",
            f"{sentiment['errors']} of {sentiment['total']} aspects are misclassified "
            f"({_share(sentiment['errors'], sentiment['total'])}).",
            "",
            "| Gold sentiment | Predicted as | Errors | Share of all errors |",
            "|---|---|---|---|",
        ]
        for (gold, predicted), count in sentiment["confusions"]:
            lines.append(f"| {gold} | {predicted} | {count} | {_share(count, sentiment['errors'])} |")
        lines += [
            "",
            "Accuracy by the confidence the model reports. If confidence carries",
            "information, accuracy rises from the first row to the last:",
            "",
            "| Confidence | Predictions | Accuracy |",
            "|---|---|---|",
        ]
        for band, count, accuracy in sentiment["bands"]:
            lines.append(f"| {band} | {count} | {'n/a' if accuracy is None else f'{accuracy:.1%}'} |")
        lines += [
            "",
            f"A random sample of misclassified aspects (seed fixed, at most {SAMPLE_SIZE}):",
            "",
            "| Sentence | Aspect | Gold | Predicted | Confidence |",
            "|---|---|---|---|---|",
        ]
        for text, aspect, gold, predicted, confidence in sentiment["sample"]:
            lines.append(f"| {text.replace('|', '/')} | {aspect} | {gold} | {predicted} | {_confidence(confidence)} |")
        lines.append("")
    return "\n".join(lines)


# Aspect extraction only. Both extraction models have a training log with the
# same settings, so the only difference between them is the training domains.
# The earlier laptops-only *sentiment* model is a checkpoint from an interrupted
# run with no training record, so its scores (and end-to-end scores, which
# depend on it) cannot be attributed to the training domains and are left out.
TRANSFER_ROWS: list[tuple[str, tuple[str, ...]]] = [
    ("Aspect extraction precision", ("aspect_extraction", "precision")),
    ("Aspect extraction recall", ("aspect_extraction", "recall")),
    ("Aspect extraction F1", ("aspect_extraction", "f1")),
]

Sample = tuple[str, str, str, list[tuple[str, str, float]]]  # domain, review, overall, aspects


def _metric(report: dict[str, Any], scope: str, path: tuple[str, ...]) -> float:
    value: Any = report["results"][scope]
    for key in path:
        value = value[key]
    return value


def render_transfer(
    laptops_only: dict[str, Any], both: dict[str, Any], samples: list[Sample], generated_at: str = ""
) -> str:
    """docs/transfer.md from two evaluation reports and the pipeline's output on samples."""
    lines = [
        "# Cross-domain transfer",
        "",
        "> Generated by `python -m training.error_analysis`. Do not edit by hand.",
        "",
        f"- Generated: {generated_at}",
        "",
        "## Measured: a laptop-trained aspect extractor on restaurant reviews",
        "",
        "The first aspect-extraction model of this project was trained on laptop reviews",
        "only, with the same settings as the deployed one. Evaluating it on the restaurant",
        "test set shows what happens on a product category the model never saw. The second",
        "column is the deployed model, trained on both domains, on the same sentences.",
        "",
        "Sentiment and end-to-end scores are not compared here. The earlier laptops-only",
        "sentiment model is a checkpoint from an interrupted training run and has no",
        "training record, so a difference in its scores could not be attributed to the",
        "training domains.",
        "",
    ]
    for scope, title in (("restaurants", "Restaurant test set (unseen domain for the laptops-only model)"),
                         ("laptops", "Laptop test set (seen by both)")):
        lines += [
            f"### {title}",
            "",
            "| Metric | Trained on laptops only | Trained on both domains | Difference |",
            "|---|---|---|---|",
        ]
        for name, path in TRANSFER_ROWS:
            old, new = _metric(laptops_only, scope, path), _metric(both, scope, path)
            lines.append(f"| {name} | {old:.4f} | {new:.4f} | {new - old:+.4f} |")
        lines.append("")
    lines += [
        "## Illustration: reviews of other product categories",
        "",
        "There is no annotated test data for other categories, so this is an illustration,",
        "not a measurement. The reviews in `data/samples/other_domains.csv` were written by",
        "hand; the table shows what the deployed pipeline returns for each. Read the",
        "aspect column and judge: an aspect that a person would not name, or a sentiment",
        "a person would not agree with, is an error.",
        "",
        "| Category | Review | Overall | Aspects found |",
        "|---|---|---|---|",
    ]
    for domain, review, overall, aspects in samples:
        found = ", ".join(f"{a} ({s}, {_confidence(c)})" for a, s, c in aspects) or "none"
        lines.append(f"| {domain} | {review.replace('|', '/')} | {overall} | {found} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit", type=int, default=None, help="use only N sentences (smoke test)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--laptops-only-report", type=Path,
                        default=MODELS_DIR / "laptops_only_report.json")
    parser.add_argument("--report", type=Path, default=MODELS_DIR / "evaluation_report.json")
    parser.add_argument("--samples", type=Path, default=DATA_DIR / "samples" / "other_domains.csv")
    parser.add_argument("--output-dir", type=Path, default=DOCS_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.nlp.pipeline import ABSAPipeline
    from training.common import load_split, refuse_limited_default

    refuse_limited_default(args.limit, args.output_dir, DOCS_DIR, "--output-dir")

    pipeline = ABSAPipeline.from_pretrained(ASPECT_MODEL_DIR, SENTIMENT_MODEL_DIR, OVERALL_MODEL_DIR)
    records = load_split("test", None, args.limit)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    per_domain: dict[str, dict[str, Any]] = {}
    for domain in sorted({r["domain"] for r in records}):
        subset = [r for r in records if r["domain"] == domain]
        logger.info("Analysing %d %s sentences", len(subset), domain)
        per_domain[domain] = {
            "extraction": analyse_extraction(pipeline.extractor, subset),
            "sentiment": analyse_sentiment(pipeline.classifier, subset, args.seed),
        }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "error_analysis.md").write_text(
        render_error_analysis(per_domain, generated_at), encoding="utf-8"
    )

    samples: list[Sample] = []
    if args.samples.exists():
        with args.samples.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                result = pipeline.analyze(row["review"])
                samples.append((
                    row["category"], result.review, result.overall_sentiment,
                    [(a.aspect, a.sentiment, a.confidence) for a in result.aspects],
                ))
    if args.laptops_only_report.exists() and args.report.exists():
        (args.output_dir / "transfer.md").write_text(
            render_transfer(
                json.loads(args.laptops_only_report.read_text(encoding="utf-8")),
                json.loads(args.report.read_text(encoding="utf-8")),
                samples, generated_at,
            ),
            encoding="utf-8",
        )
    else:
        logger.warning("transfer.md not written: needs %s and %s", args.laptops_only_report, args.report)
    logger.info("Written to %s", args.output_dir)


if __name__ == "__main__":
    main()
