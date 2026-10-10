"""Evaluate the trained models on the held-out test set.

Run from the ``backend`` directory, after both models have been trained:

    python -m training.evaluate

Four evaluations, all on the official SemEval-2014 gold test data:

1. Aspect extraction      - exact-match span precision / recall / F1.
2. Aspect sentiment       - accuracy, P/R/F1, confusion matrix, given the GOLD
                            aspects (isolates the classifier's quality), plus
                            accuracy on sentences with mixed sentiments.
3. Overall sentiment      - same metrics against weak sentence labels.
4. End-to-end ABSA        - P/R/F1 of (aspect, sentiment) pairs produced by the
                            full pipeline: an item is correct only if the
                            aspect span AND its sentiment are both right.

Outputs: ``models/evaluation_report.json``, ``docs/results.md`` and two
confusion-matrix figures in ``docs/figures``. Nothing in those files is typed
by hand - rerun this script to regenerate them.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.aspect_model import AspectExtractor
from app.models.sentiment_model import SentimentClassifier
from app.nlp.aspect_extraction import extract_aspects
from app.nlp.labels import SENTIMENT_LABELS
from app.nlp.preprocessing import Sentence, tokenize
from app.nlp.sentiment import classify_aspects
from app.paths import (
    ASPECT_MODEL_DIR,
    DOCS_DIR,
    MODELS_DIR,
    OVERALL_MODEL_DIR,
    SENTIMENT_MODEL_DIR,
)
from training.common import configure_logging, load_split, refuse_limited_default
from training.metrics import span_prf
from training.train_aspect import evaluate_extraction
from training.train_sentiment import aspect_examples, evaluate_sentiment, sentence_examples

logger = logging.getLogger("evaluate")


def evaluate_end_to_end(
    extractor: AspectExtractor, classifier: SentimentClassifier, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Score (aspect span, sentiment) pairs predicted from raw text alone."""
    gold: list[set[tuple[int, int, str]]] = []
    conflict_spans: list[set[tuple[int, int]]] = []
    extracted = []
    for record in records:
        text = record["text"]
        tokens = tokenize(text)
        gold_items: set[tuple[int, int, str]] = set()
        conflicts: set[tuple[int, int]] = set()
        for aspect in record["aspects"]:
            # Snap the annotation to whole tokens, exactly as done for training.
            inside = [t for t in tokens if t.start < aspect["to"] and t.end > aspect["from"]]
            span = (inside[0].start, inside[-1].end)
            if aspect["polarity"] == "conflict":
                conflicts.add(span)
            else:
                gold_items.add((*span, aspect["polarity"]))
        gold.append(gold_items)
        conflict_spans.append(conflicts)
        extracted.append(extract_aspects(extractor, text, [Sentence(text, 0, len(text))]))

    flat = [aspect for aspects in extracted for aspect in aspects]
    sentiments = iter(classify_aspects(classifier, flat))
    predicted: list[set[tuple[int, int, str]]] = []
    for aspects, conflicts in zip(extracted, conflict_spans):
        items = {(a.start, a.end, next(sentiments).label) for a in aspects}
        # 'conflict' aspects have no 3-class label, so they are left out of
        # both the gold set and the predictions instead of counting as errors.
        predicted.append({item for item in items if item[:2] not in conflicts})
    return span_prf(gold, predicted)


def evaluate_by_sentence_type(
    classifier: SentimentClassifier, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Aspect-sentiment accuracy, split by whether the sentence mixes sentiments.

    In a "uniform" sentence all aspects share one polarity, so a model can be
    right without looking at the aspect at all. In a "mixed" sentence it cannot:
    this subset shows whether the model really is aspect-specific.
    """
    result: dict[str, Any] = {}
    for name, want_mixed in (("uniform", False), ("mixed", True)):
        subset = []
        for record in records:
            polarities = {a["polarity"] for a in record["aspects"] if a["polarity"] != "conflict"}
            if (len(polarities) > 1) == want_mixed:
                subset.append(record)
        examples = aspect_examples(subset)
        if examples:
            metrics = evaluate_sentiment(classifier, examples)
            result[name] = {
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro"]["f1"],
                "support": metrics["support"],
            }
        else:
            result[name] = {"accuracy": None, "macro_f1": None, "support": 0}
    return result


def evaluate_models(
    extractor: AspectExtractor,
    classifier: SentimentClassifier,
    overall_classifier: SentimentClassifier,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "test_sentences": len(records),
        "aspect_extraction": evaluate_extraction(extractor, records),
        "aspect_sentiment": evaluate_sentiment(classifier, aspect_examples(records)),
        "aspect_sentiment_by_sentence_type": evaluate_by_sentence_type(classifier, records),
        "overall_sentiment": evaluate_sentiment(overall_classifier, sentence_examples(records)),
        "end_to_end": evaluate_end_to_end(extractor, classifier, records),
    }


def _read_training_log(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "training_log.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def plot_confusion_matrix(confusion: dict[str, Any], title: str, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")  # render to a file; no display needed
    import matplotlib.pyplot as plt

    labels, matrix = confusion["labels"], confusion["matrix"]
    figure, axis = plt.subplots(figsize=(5, 4.2))
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xticks(range(len(labels)), labels)
    axis.set_yticks(range(len(labels)), labels)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("True")
    axis.set_title(title)
    threshold = max(max(row) for row in matrix) / 2
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            axis.text(j, i, str(value), ha="center", va="center",
                      color="white" if value > threshold else "black")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _prf_row(name: str, m: dict[str, Any]) -> str:
    return f"| {name} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} |"


def _classification_section(title: str, metrics: dict[str, Any]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        f"Examples: {metrics['support']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Accuracy | {metrics['accuracy']:.4f} |",
        f"| Precision (macro) | {metrics['macro']['precision']:.4f} |",
        f"| Recall (macro) | {metrics['macro']['recall']:.4f} |",
        f"| F1-score (macro) | {metrics['macro']['f1']:.4f} |",
        f"| F1-score (weighted) | {metrics['weighted']['f1']:.4f} |",
        "",
        "| Class | Precision | Recall | F1-score | Support |",
        "|---|---|---|---|---|",
    ]
    for label, m in metrics["per_class"].items():
        lines.append(
            f"| {label} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['support']} |"
        )
    labels = metrics["confusion_matrix"]["labels"]
    lines += [
        "",
        "Confusion matrix (rows = true class, columns = predicted class):",
        "",
        "| true \\ predicted | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for label, row in zip(labels, metrics["confusion_matrix"]["matrix"]):
        lines.append(f"| **{label}** | " + " | ".join(str(v) for v in row) + " |")
    return lines + [""]


def render_markdown(report: dict[str, Any]) -> str:
    """Build docs/results.md from the report. Every number comes from ``report``."""
    lines = [
        "# Evaluation results",
        "",
        "> Generated by `python -m training.evaluate`. Do not edit by hand: rerun the",
        "> script after retraining and this file is rewritten from the new predictions.",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Test data: SemEval-2014 Task 4 gold test set, domains: {', '.join(report['domains'])}",
        f"- Test sentences: {report['results']['all']['test_sentences']}",
        "",
        "## Training setup",
        "",
        "| | Aspect extraction | Aspect sentiment | Overall sentiment |",
        "|---|---|---|---|",
    ]
    logs = [report["training"][name] for name in ("aspect", "sentiment", "overall")]

    def cell(log: dict[str, Any], *keys: str) -> str:
        value: Any = log
        for key in keys:
            value = value.get(key, "n/a") if isinstance(value, dict) else "n/a"
        if isinstance(value, float) and keys[-1] == "best_validation_score":
            return f"{value:.4f}"
        return ", ".join(map(str, value)) if isinstance(value, list) else str(value)

    for label, keys in [
        ("Base model", ("hyperparameters", "model_name")),
        ("Training domains", ("hyperparameters", "domains")),
        ("Epochs", ("hyperparameters", "epochs")),
        ("Batch size", ("hyperparameters", "batch_size")),
        ("Learning rate", ("hyperparameters", "lr")),
        ("Max sequence length", ("hyperparameters", "max_length")),
        ("Seed", ("hyperparameters", "seed")),
        ("Best epoch (validation)", ("best_epoch",)),
        ("Model-selection metric", ("selection_metric",)),
        ("Best validation score", ("best_validation_score",)),
        ("Training time (minutes)", ("training_minutes",)),
        ("Device", ("device",)),
    ]:
        lines.append(f"| {label} | " + " | ".join(cell(log, *keys) for log in logs) + " |")
    lines += [
        f"| Training examples | {cell(logs[0], 'data', 'train_sentences')} sentences | "
        f"{cell(logs[1], 'data', 'train_examples')} (sentence, aspect) pairs | "
        f"{cell(logs[2], 'data', 'train_examples')} sentences |",
        "",
    ]

    for scope, results in report["results"].items():
        heading = "All evaluated domains" if scope == "all" else f"Domain: {scope}"
        lines += [
            f"## {heading}",
            "",
            f"Test sentences: {results['test_sentences']}",
            "",
            "### Aspect extraction and end-to-end ABSA",
            "",
            "Exact match: a predicted aspect counts only if both of its boundaries equal the",
            "annotation. End-to-end additionally requires the predicted sentiment to be correct.",
            "",
            "| Task | Precision | Recall | F1-score |",
            "|---|---|---|---|",
            _prf_row("Aspect extraction", results["aspect_extraction"]),
            _prf_row("End-to-end (aspect + sentiment)", results["end_to_end"]),
            "",
            f"Gold aspects: {results['aspect_extraction']['gold']}, predicted: "
            f"{results['aspect_extraction']['predicted']}, correct: "
            f"{results['aspect_extraction']['true_positives']}.",
            "",
        ]
        lines += _classification_section(
            "Aspect sentiment classification (gold aspects given)", results["aspect_sentiment"]
        )
        if scope == "all":
            lines += ["![Confusion matrix](figures/sentiment_confusion_matrix.png)", ""]
        by_type = results["aspect_sentiment_by_sentence_type"]
        lines += [
            "Accuracy by sentence type. In a *uniform* sentence every aspect has the same",
            "sentiment; in a *mixed* sentence the aspects differ, so the model must be",
            "aspect-specific to be right:",
            "",
            "| Sentence type | Aspects | Accuracy | F1-score (macro) |",
            "|---|---|---|---|",
        ]
        for name in ("uniform", "mixed"):
            m = by_type[name]
            scores = f"{m['accuracy']:.4f} | {m['macro_f1']:.4f}" if m["support"] else "n/a | n/a"
            lines.append(f"| {name} | {m['support']} | {scores} |")
        lines.append("")
        lines += _classification_section(
            "Overall (sentence-level) sentiment - weak labels", results["overall_sentiment"]
        )
        if scope == "all":
            lines += [
                "![Overall-sentiment confusion matrix](figures/overall_confusion_matrix.png)",
                "",
            ]
    lines += [
        "## Notes for interpreting these numbers",
        "",
        "- 'conflict' aspects are excluded from sentiment evaluation (3-class setting).",
        "- Overall-sentiment labels are not human annotations: they are derived from the",
        "  aspect polarities of each sentence (majority of positive vs. negative, neutral",
        "  on a tie). Treat that table as indicative only.",
        "- All numbers come from a single training run (one seed).",
        "- Models trained by `training.run_all` are selected over the previously deployed models by comparing test-set scores",
        "  (`training.promote`: span F1 for aspect extraction, macro-F1 for sentiment).",
        "  Choosing between two models on the test set makes these numbers slightly",
        "  optimistic as an estimate for unseen reviews.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], report_path: Path, markdown_path: Path) -> None:
    """Write the report, the tables and both figures, so they always describe one run."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    figures = markdown_path.parent / "figures"
    summary = report["results"]["all"]
    plot_confusion_matrix(
        summary["aspect_sentiment"]["confusion_matrix"],
        "Aspect sentiment - test set",
        figures / "sentiment_confusion_matrix.png",
    )
    plot_confusion_matrix(
        summary["overall_sentiment"]["confusion_matrix"],
        "Overall sentiment - test set (weak labels)",
        figures / "overall_confusion_matrix.png",
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--aspect-model-dir", type=Path, default=ASPECT_MODEL_DIR)
    parser.add_argument("--sentiment-model-dir", type=Path, default=SENTIMENT_MODEL_DIR)
    parser.add_argument("--overall-model-dir", type=Path, default=OVERALL_MODEL_DIR)
    parser.add_argument("--domains", nargs="+", default=None,
                        help="test domains (default: the domains the aspect model was trained on)")
    parser.add_argument("--limit", type=int, default=None, help="use only N sentences (smoke test)")
    parser.add_argument("--report", type=Path, default=MODELS_DIR / "evaluation_report.json")
    parser.add_argument("--markdown", type=Path, default=DOCS_DIR / "results.md")
    args = parser.parse_args()
    refuse_limited_default(args.limit, args.report, MODELS_DIR / "evaluation_report.json", "--report")
    refuse_limited_default(args.limit, args.markdown, DOCS_DIR / "results.md", "--markdown")
    # The figures are written next to the markdown file, whatever it is called.
    refuse_limited_default(args.limit, args.markdown.parent, DOCS_DIR, "--markdown")
    configure_logging()

    training = {
        "aspect": _read_training_log(args.aspect_model_dir),
        "sentiment": _read_training_log(args.sentiment_model_dir),
        "overall": _read_training_log(args.overall_model_dir),
    }
    domains = args.domains or training["aspect"].get("hyperparameters", {}).get("domains")
    records = load_split("test", domains, args.limit)
    domains = sorted({r["domain"] for r in records})

    max_length = training["aspect"].get("hyperparameters", {}).get("max_length", 128)
    extractor = AspectExtractor.from_pretrained(args.aspect_model_dir, max_length)
    classifier = SentimentClassifier.from_pretrained(args.sentiment_model_dir, max_length)
    overall_classifier = SentimentClassifier.from_pretrained(args.overall_model_dir, max_length)

    results: dict[str, Any] = {}
    logger.info("Evaluating on %d test sentences (%s)", len(records), ", ".join(domains))
    results["all"] = evaluate_models(extractor, classifier, overall_classifier, records)
    if len(domains) > 1:
        for domain in domains:
            logger.info("Evaluating domain %s", domain)
            results[domain] = evaluate_models(
                extractor, classifier, overall_classifier,
                [r for r in records if r["domain"] == domain],
            )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": "SemEval-2014 Task 4, gold test set",
        "domains": domains,
        "training": training,
        "results": results,
    }
    write_outputs(report, args.report, args.markdown)

    summary = results["all"]
    print(f"\nTest sentences: {summary['test_sentences']}  ({', '.join(domains)})")
    for name in ("aspect_extraction", "end_to_end"):
        m = summary[name]
        print(f"{name:20s} P {m['precision']:.4f}  R {m['recall']:.4f}  F1 {m['f1']:.4f}")
    for name in ("aspect_sentiment", "overall_sentiment"):
        m = summary[name]
        print(f"{name:20s} accuracy {m['accuracy']:.4f}  macro-F1 {m['macro']['f1']:.4f}")
    for name, m in summary["aspect_sentiment_by_sentence_type"].items():
        if m["support"]:
            print(f"  aspects in {name} sentences: accuracy {m['accuracy']:.4f}  (n={m['support']})")
    print(f"\nReport: {args.report}\nTables: {args.markdown}")


if __name__ == "__main__":
    main()
