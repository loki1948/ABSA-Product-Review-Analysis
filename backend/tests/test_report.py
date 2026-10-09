from __future__ import annotations

from typing import Any

import pytest

from app.nlp.labels import SENTIMENT_LABELS
from training.metrics import classification_metrics, span_prf
from training.report import render_report


def scope(shift: float = 0.0) -> dict[str, Any]:
    sentiment = classification_metrics(
        ["positive", "negative", "neutral", "positive"],
        ["positive", "negative", "positive", "positive"],
        SENTIMENT_LABELS,
    )
    spans = span_prf([{(0, 1)}, {(2, 3)}], [{(0, 1)}, set()])
    spans = {**spans, "f1": spans["f1"] + shift}
    return {
        "test_sentences": 800,
        "aspect_extraction": spans,
        "aspect_sentiment": sentiment,
        "aspect_sentiment_by_sentence_type": {
            "uniform": {"accuracy": 0.9, "macro_f1": 0.8, "support": 3},
            "mixed": {"accuracy": 0.5, "macro_f1": 0.4, "support": 1},
        },
        "overall_sentiment": sentiment,
        "end_to_end": spans,
    }


LOG = {
    "hyperparameters": {"model_name": "bert-base-uncased", "domains": ["laptops", "restaurants"],
                        "epochs": 3, "batch_size": 16, "lr": 3e-05, "max_length": 128, "seed": 42},
    "best_epoch": 3, "best_validation_score": 0.83, "training_minutes": 78.2, "device": "cpu",
}


@pytest.fixture
def inputs() -> dict[str, Any]:
    results = {"all": scope(), "laptops": scope(), "restaurants": scope()}
    return {
        "bert": {"generated_at": "2026-10-10T02:00:00+00:00", "domains": ["laptops", "restaurants"],
                 "training": {"aspect": LOG, "sentiment": LOG, "overall": LOG}, "results": results},
        "baseline": {"results": {"all": scope(-0.4), "laptops": scope(-0.4), "restaurants": scope(-0.4)}},
        "laptops_only": {"results": {"all": scope(-0.1), "laptops": scope(), "restaurants": scope(-0.2)}},
        "dataset": {"splits": {
            "train": {"laptops": {"sentences": 2723, "aspect_terms": 2131},
                      "restaurants": {"sentences": 2726, "aspect_terms": 3322}},
            "val": {"laptops": {"sentences": 303, "aspect_terms": 200},
                    "restaurants": {"sentences": 303, "aspect_terms": 377}},
            "test": {"laptops": {"sentences": 800, "aspect_terms": 654},
                     "restaurants": {"sentences": 800, "aspect_terms": 1134}},
        }},
    }


def test_report_has_every_section(inputs: dict[str, Any]) -> None:
    text = render_report(**inputs)
    for heading in ("## Abstract", "## 1. Introduction", "## 2. Dataset", "## 3. Method",
                    "## 4. System", "## 5. Experimental setup", "## 6. Results",
                    "## 7. Error analysis", "## 8. Limitations", "## 9. Conclusion", "## References"):
        assert heading in text, heading


def test_report_numbers_come_from_the_reports(inputs: dict[str, Any]) -> None:
    text = render_report(**inputs)
    f1 = inputs["bert"]["results"]["all"]["aspect_extraction"]["f1"]
    assert f"| Aspect extraction F1 | {f1 - 0.4:.4f} | {f1:.4f} | +0.4000 |" in text
    assert "| laptops | 2723 | 303 | 800 |" in text
    assert "78.2" in text


def test_report_states_the_transfer_gap_on_restaurants(inputs: dict[str, Any]) -> None:
    text = render_report(**inputs)
    f1 = inputs["bert"]["results"]["restaurants"]["aspect_extraction"]["f1"]
    assert f"| Aspect extraction F1 | {f1 - 0.2:.4f} | {f1:.4f} | +0.2000 |" in text


def test_report_can_be_written_without_the_optional_reports(inputs: dict[str, Any]) -> None:
    text = render_report(inputs["bert"], None, None, inputs["dataset"])
    assert "## 6. Results" in text
    assert "not available" in text


def test_slides_use_the_same_numbers_as_the_report(inputs: dict[str, Any]) -> None:
    from training.report import render_slides

    text = render_slides(**inputs)
    f1 = inputs["bert"]["results"]["all"]["aspect_extraction"]["f1"]
    assert text.startswith("---\nmarp: true")
    assert f"| Aspect extraction F1 | {f1 - 0.4:.3f} | {f1:.3f} |" in text
    assert text.count("\n---\n") >= 10, "one slide per separator"


def test_slides_do_not_claim_missing_comparisons(inputs: dict[str, Any]) -> None:
    from training.report import render_slides

    text = render_slides(inputs["bert"], None, None, inputs["dataset"])
    assert "Baseline" not in text
    assert "laptops only" not in text
