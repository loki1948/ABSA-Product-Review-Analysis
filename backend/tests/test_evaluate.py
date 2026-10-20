from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.nlp.labels import SENTIMENT_LABELS
from app.paths import (
    ASPECT_MODEL_DIR,
    DOCS_DIR,
    MODELS_DIR,
    OVERALL_MODEL_DIR,
    SENTIMENT_MODEL_DIR,
)
from tests.conftest import requires_models
from training.evaluate import render_markdown, write_outputs
from training.metrics import classification_metrics, span_prf

PUBLISHED_REPORT = MODELS_DIR / "evaluation_report.json"


@pytest.fixture
def report() -> dict[str, Any]:
    """A small report with the layout ``training.evaluate`` writes."""
    truth = ["positive", "negative", "neutral", "positive"]
    predicted = ["positive", "negative", "positive", "positive"]
    sentiment = classification_metrics(truth, predicted, SENTIMENT_LABELS)
    spans = span_prf([{(0, 1)}, {(2, 3)}], [{(0, 1)}, set()])
    log = {"hyperparameters": {"model_name": "bert-base-uncased", "domains": ["laptops"]},
           "data": {"train_sentences": 4, "train_examples": 4}}
    return {
        "generated_at": "2026-10-09T12:00:00+00:00",
        "dataset": "SemEval-2014 Task 4, gold test set",
        "domains": ["laptops"],
        "training": {"aspect": log, "sentiment": log, "overall": log},
        "results": {
            "all": {
                "test_sentences": 2,
                "aspect_extraction": spans,
                "aspect_sentiment": sentiment,
                "aspect_sentiment_by_sentence_type": {
                    "uniform": {"accuracy": 1.0, "macro_f1": 1.0, "support": 3},
                    "mixed": {"accuracy": 0.0, "macro_f1": 0.0, "support": 1},
                },
                "overall_sentiment": sentiment,
                "end_to_end": spans,
            }
        },
    }


def test_results_embed_both_confusion_matrices(report: dict[str, Any]) -> None:
    text = render_markdown(report)
    assert "figures/sentiment_confusion_matrix.png" in text
    assert "figures/overall_confusion_matrix.png" in text


def test_results_state_how_the_models_were_selected(report: dict[str, Any]) -> None:
    assert (
        "selected over the previously deployed models by comparing test-set scores"
        in render_markdown(report)
    )


def test_results_include_the_mixed_sentence_row(report: dict[str, Any]) -> None:
    assert "| mixed | 1 | 0.0000 | 0.0000 |" in render_markdown(report)


def test_outputs_are_written_together(report: dict[str, Any], tmp_path: Path) -> None:
    write_outputs(report, tmp_path / "report.json", tmp_path / "docs" / "results.md")
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8")) == report
    assert (tmp_path / "docs" / "results.md").exists()
    assert (tmp_path / "docs" / "figures" / "sentiment_confusion_matrix.png").stat().st_size > 0
    assert (tmp_path / "docs" / "figures" / "overall_confusion_matrix.png").stat().st_size > 0


def test_published_results_match_the_published_report() -> None:
    if not PUBLISHED_REPORT.exists():
        pytest.skip("no evaluation report yet")
    published = json.loads(PUBLISHED_REPORT.read_text(encoding="utf-8"))
    results = (DOCS_DIR / "results.md").read_text(encoding="utf-8")
    assert f"- Generated: {published['generated_at']}" in results


@pytest.mark.model
@requires_models
def test_report_describes_the_deployed_models() -> None:
    """Fails when the models were retrained or swapped without re-running the evaluation."""
    published = json.loads(PUBLISHED_REPORT.read_text(encoding="utf-8"))
    for key, folder in (
        ("aspect", ASPECT_MODEL_DIR),
        ("sentiment", SENTIMENT_MODEL_DIR),
        ("overall", OVERALL_MODEL_DIR),
    ):
        log = json.loads((folder / "training_log.json").read_text(encoding="utf-8"))
        assert published["training"][key]["best_validation_score"] == log["best_validation_score"]
        assert published["training"][key]["training_minutes"] == log["training_minutes"]
    assert published["domains"] == ["laptops", "restaurants"]
    assert "aspect_sentiment_by_sentence_type" in published["results"]["all"]


def test_limit_cannot_overwrite_published_or_deployed_outputs(tmp_path: Path) -> None:
    """`--limit` is for trying a script out; its toy output must not replace real files."""
    from training.common import refuse_limited_default

    with pytest.raises(SystemExit, match="--limit"):
        refuse_limited_default(32, DOCS_DIR / "results.md", DOCS_DIR / "results.md", "--markdown")
    refuse_limited_default(32, tmp_path / "results.md", DOCS_DIR / "results.md", "--markdown")
    refuse_limited_default(None, DOCS_DIR / "results.md", DOCS_DIR / "results.md", "--markdown")


def test_validation_score_is_rounded_in_the_training_table(report: dict[str, Any]) -> None:
    for log in report["training"].values():
        log["best_validation_score"] = 0.8312342569269521
    text = render_markdown(report)
    assert "| Best validation score | 0.8312 | 0.8312 | 0.8312 |" in text
    assert "0.8312342569269521" not in text


def test_limit_cannot_overwrite_the_published_figures(tmp_path: Path) -> None:
    """Figures are written next to the markdown file, whatever it is called."""
    from training.common import refuse_limited_default

    with pytest.raises(SystemExit, match="--limit"):
        refuse_limited_default(32, (DOCS_DIR / "try.md").parent, DOCS_DIR, "--markdown")
    refuse_limited_default(32, (tmp_path / "try.md").parent, DOCS_DIR, "--markdown")


def test_limit_run_writing_into_docs_is_refused_by_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Third review: the guard must be in main(), not only in the helper."""
    import sys

    from training import evaluate

    monkeypatch.setattr(sys, "argv", [
        "evaluate", "--limit", "32", "--report", str(tmp_path / "report.json"),
        "--markdown", str(DOCS_DIR / "try.md"),
    ])
    with pytest.raises(SystemExit, match="--limit"):
        evaluate.main()
    assert not (DOCS_DIR / "try.md").exists()
