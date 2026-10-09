"""A baseline without BERT: noun phrases as aspects, a word list for sentiment.

Run from the ``backend`` directory:

    python -m training.baseline

It answers the question "what do the BERT models add?" by solving the same
tasks with rules, scored by the same metric functions on the same test data:

* Aspect extraction - every maximal run of nouns (part-of-speech tags NN, NNS)
  is one aspect, so "battery life" is found as one two-word aspect.
* Aspect sentiment  - opinion words from the Hu and Liu (2004) lexicon are
  counted inside the aspect's clause; a negation word shortly before an
  opinion word flips it. More positive than negative words -> positive, the
  opposite -> negative, a tie (usually: no opinion word) -> neutral.
* Overall sentiment - the same count over the whole sentence.

Outputs: ``models/baseline_report.json`` and ``docs/baseline.md``, which places
the baseline next to the BERT results from ``models/evaluation_report.json``.

This module is for evaluation only. The application's pipeline (``app/nlp``)
uses learnt models for both stages and does not import it.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.nlp.labels import SENTIMENT_LABELS
from app.nlp.preprocessing import bio_to_spans, extract_context, tokenize
from app.paths import DOCS_DIR, MODELS_DIR
from training.common import load_split, sentence_level_label
from training.metrics import classification_metrics, span_prf

logger = logging.getLogger("baseline")

Tagger = Callable[[list[str]], list[str]]

NOUN_TAGS = {"NN", "NNS"}
NEGATIONS = {"not", "no", "never", "without", "hardly"}
NEGATION_WINDOW = 3  # an opinion word is flipped by a negation up to this many words before it
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def noun_runs(pos_tags: list[str]) -> list[tuple[int, int]]:
    """``(first_token, last_token_exclusive)`` of every maximal run of common nouns.

    The same span format as ``bio_to_spans``, so both can be scored together.
    """
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, tag in enumerate(pos_tags):
        if tag in NOUN_TAGS:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(pos_tags)))
    return runs


class LexiconClassifier:
    """Sentiment from counting opinion words; no training involved."""

    def __init__(self, positive: set[str], negative: set[str]) -> None:
        self.positive = positive
        self.negative = negative

    def score(self, text: str) -> int:
        """Positive minus negative opinion words in ``text``, after negation."""
        words = _WORD.findall(text.lower())
        total = 0
        for index, word in enumerate(words):
            value = 1 if word in self.positive else -1 if word in self.negative else 0
            if value == 0:
                continue
            before = words[max(0, index - NEGATION_WINDOW) : index]
            if any(w in NEGATIONS or w.endswith("n't") for w in before):
                value = -value
            total += value
        return total

    def predict(self, texts: list[str], aspects: list[str | None] | None = None) -> list[str]:
        """One label per text; with an aspect, only the aspect's clause is read."""
        aspects = aspects or [None] * len(texts)
        labels: list[str] = []
        for text, aspect in zip(texts, aspects):
            scope = text
            if aspect is not None:
                start = text.lower().find(aspect.lower())
                if start >= 0:
                    scope = extract_context(text, start, start + len(aspect))
            score = self.score(scope)
            labels.append("positive" if score > 0 else "negative" if score < 0 else "neutral")
        return labels


def load_lexicon() -> LexiconClassifier:
    """The Hu and Liu opinion lexicon shipped with NLTK (about 6800 words)."""
    import nltk
    from nltk.corpus import opinion_lexicon

    try:
        opinion_lexicon.positive()
    except LookupError:
        nltk.download("opinion_lexicon", quiet=True)
    return LexiconClassifier(set(opinion_lexicon.positive()), set(opinion_lexicon.negative()))


def nltk_tagger() -> Tagger:
    """Part-of-speech tagger: tokens in, one Penn Treebank tag per token out."""
    import nltk

    try:
        nltk.pos_tag(["test"])
    except LookupError:
        nltk.download("averaged_perceptron_tagger_eng", quiet=True)
    return lambda tokens: [tag for _, tag in nltk.pos_tag(tokens)]


def evaluate_baseline(
    records: list[dict[str, Any]], tagger: Tagger, classifier: LexiconClassifier
) -> dict[str, Any]:
    """The four evaluations of ``training.evaluate``, for the rule-based system."""
    runs = [noun_runs(tagger(r["tokens"])) for r in records]

    extraction = span_prf(
        [set(bio_to_spans(r["tags"])) for r in records], [set(found) for found in runs]
    )

    pairs = [
        (r["text"], a["term"], a["polarity"])
        for r in records for a in r["aspects"] if a["polarity"] in SENTIMENT_LABELS
    ]
    aspect_sentiment = classification_metrics(
        [p[2] for p in pairs],
        classifier.predict([p[0] for p in pairs], [p[1] for p in pairs]),
        SENTIMENT_LABELS,
    )

    sentences = [
        (r["text"], label)
        for r in records
        if (label := sentence_level_label([a["polarity"] for a in r["aspects"]])) is not None
    ]
    overall = classification_metrics(
        [s[1] for s in sentences], classifier.predict([s[0] for s in sentences]), SENTIMENT_LABELS
    )

    # End to end: character spans, as in training.evaluate.evaluate_end_to_end.
    gold: list[set[tuple[int, int, str]]] = []
    predicted: list[set[tuple[int, int, str]]] = []
    for record, found in zip(records, runs):
        text, tokens = record["text"], tokenize(record["text"])
        gold_items: set[tuple[int, int, str]] = set()
        conflicts: set[tuple[int, int]] = set()
        for aspect in record["aspects"]:
            inside = [t for t in tokens if t.start < aspect["to"] and t.end > aspect["from"]]
            span = (inside[0].start, inside[-1].end)
            if aspect["polarity"] == "conflict":
                conflicts.add(span)
            else:
                gold_items.add((*span, aspect["polarity"]))
        spans = [(tokens[first].start, tokens[end - 1].end) for first, end in found if end <= len(tokens)]
        labels = classifier.predict([text] * len(spans), [text[s:e] for s, e in spans])
        gold.append(gold_items)
        predicted.append({(*span, label) for span, label in zip(spans, labels) if span not in conflicts})

    return {
        "test_sentences": len(records),
        "aspect_extraction": extraction,
        "aspect_sentiment": aspect_sentiment,
        "overall_sentiment": overall,
        "end_to_end": span_prf(gold, predicted),
    }


ROWS: list[tuple[str, tuple[str, ...]]] = [
    ("Aspect extraction precision", ("aspect_extraction", "precision")),
    ("Aspect extraction recall", ("aspect_extraction", "recall")),
    ("Aspect extraction F1", ("aspect_extraction", "f1")),
    ("Aspect sentiment accuracy", ("aspect_sentiment", "accuracy")),
    ("Aspect sentiment macro-F1", ("aspect_sentiment", "macro", "f1")),
    ("Overall sentiment accuracy", ("overall_sentiment", "accuracy")),
    ("Overall sentiment macro-F1", ("overall_sentiment", "macro", "f1")),
    ("End-to-end F1", ("end_to_end", "f1")),
]


def _value(results: dict[str, Any] | None, path: tuple[str, ...]) -> float | None:
    value: Any = results
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def render_markdown(baseline: dict[str, Any], bert: dict[str, Any] | None) -> str:
    """docs/baseline.md. ``bert`` is the BERT evaluation report, if there is one."""
    lines = [
        "# Baseline comparison",
        "",
        "> Generated by `python -m training.baseline`. Do not edit by hand.",
        "",
        f"- Generated: {baseline['generated_at']}",
        f"- Test data: SemEval-2014 Task 4 gold test set, domains: {', '.join(baseline['domains'])}",
        "",
        "The baseline uses no trained model. Aspects are runs of nouns found by a",
        "part-of-speech tagger; sentiment is a count of opinion words from the Hu and Liu",
        "(2004) lexicon in the aspect's clause, with a simple negation rule. Both systems",
        "are scored by the same functions on the same sentences, so the difference column",
        "is what the fine-tuned BERT models add.",
        "",
    ]
    for scope, results in baseline["results"].items():
        heading = "All evaluated domains" if scope == "all" else f"Domain: {scope}"
        bert_results = (bert or {}).get("results", {}).get(scope)
        lines += [
            f"## {heading}",
            "",
            f"Test sentences: {results['test_sentences']}",
            "",
            "| Metric | Baseline | BERT | Difference |",
            "|---|---|---|---|",
        ]
        for name, path in ROWS:
            ours, theirs = _value(results, path), _value(bert_results, path)
            if theirs is None:
                lines.append(f"| {name} | {ours:.4f} | n/a | n/a |")
            else:
                lines.append(f"| {name} | {ours:.4f} | {theirs:.4f} | {theirs - ours:+.4f} |")
        lines.append("")
    lines += [
        "## Reading the table",
        "",
        "- A noun run is a generous guess: most nouns are not aspects, so the baseline's",
        "  precision is low even where its recall is reasonable.",
        "- The lexicon has no entry for domain phrases such as \"runs hot\" or \"long wait\",",
        "  and predicts neutral whenever it finds no opinion word.",
        "- Overall-sentiment labels are derived from aspect polarities, not annotated",
        "  (see methodology, section 4.3).",
        "",
        "Reference: Hu, M. and Liu, B. (2004). Mining and Summarizing Customer Reviews. *KDD 2004*.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--domains", nargs="+", default=["laptops", "restaurants"])
    parser.add_argument("--limit", type=int, default=None, help="use only N sentences (smoke test)")
    parser.add_argument("--report", type=Path, default=MODELS_DIR / "baseline_report.json")
    parser.add_argument("--markdown", type=Path, default=DOCS_DIR / "baseline.md")
    parser.add_argument("--bert-report", type=Path, default=MODELS_DIR / "evaluation_report.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    records = load_split("test", args.domains, args.limit)
    domains = sorted({r["domain"] for r in records})
    tagger, classifier = nltk_tagger(), load_lexicon()

    results = {"all": evaluate_baseline(records, tagger, classifier)}
    if len(domains) > 1:
        for domain in domains:
            results[domain] = evaluate_baseline(
                [r for r in records if r["domain"] == domain], tagger, classifier
            )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": "SemEval-2014 Task 4, gold test set",
        "domains": domains,
        "method": "noun runs (NLTK POS tagger) + Hu and Liu opinion lexicon",
        "results": results,
    }
    bert = (
        json.loads(args.bert_report.read_text(encoding="utf-8")) if args.bert_report.exists() else None
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report, bert), encoding="utf-8")

    summary = results["all"]
    logger.info("aspect extraction F1 %.4f, aspect sentiment macro-F1 %.4f, end-to-end F1 %.4f",
                summary["aspect_extraction"]["f1"], summary["aspect_sentiment"]["macro"]["f1"],
                summary["end_to_end"]["f1"])
    logger.info("Report: %s  Tables: %s", args.report, args.markdown)


if __name__ == "__main__":
    main()
