from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from training.promote import decision_values, promote, render_comparison, verdict


def scope_results(aspect_f1: float, sentiment_f1: float, overall_f1: float) -> dict[str, Any]:
    return {
        "aspect_extraction": {"precision": aspect_f1, "recall": aspect_f1, "f1": aspect_f1},
        "end_to_end": {"f1": aspect_f1 * sentiment_f1},
        "aspect_sentiment": {"accuracy": sentiment_f1, "macro": {"f1": sentiment_f1}},
        "aspect_sentiment_by_sentence_type": {"mixed": {"accuracy": 0.5, "support": 10}},
        "overall_sentiment": {"accuracy": overall_f1, "macro": {"f1": overall_f1}},
    }


def report(aspect: float, sentiment: float, overall: float) -> dict[str, Any]:
    return {"results": {scope: scope_results(aspect, sentiment, overall)
                        for scope in ("all", "laptops", "restaurants")}}


def test_higher_everywhere_is_promoted() -> None:
    assert verdict({"all": 0.70, "laptops": 0.79, "restaurants": 0.55},
                   {"all": 0.82, "laptops": 0.80, "restaurants": 0.84}) == "promote"


def test_small_drop_on_one_domain_is_tolerated() -> None:
    assert verdict({"all": 0.70, "laptops": 0.790, "restaurants": 0.55},
                   {"all": 0.82, "laptops": 0.781, "restaurants": 0.84}) == "promote"


def test_larger_drop_on_one_domain_needs_a_decision() -> None:
    assert verdict({"all": 0.70, "laptops": 0.79, "restaurants": 0.55},
                   {"all": 0.82, "laptops": 0.77, "restaurants": 0.84}) == "needs decision"


def test_not_better_overall_needs_a_decision() -> None:
    same = {"all": 0.82, "laptops": 0.80, "restaurants": 0.84}
    assert verdict(same, dict(same)) == "needs decision"


def test_model_with_nothing_deployed_is_promoted() -> None:
    assert verdict(None, {"all": 0.7, "laptops": 0.7, "restaurants": 0.7}) == "promote (nothing deployed)"


def test_decision_metric_is_span_f1_for_extraction_and_macro_f1_for_sentiment() -> None:
    values = report(aspect=0.8, sentiment=0.7, overall=0.6)
    assert decision_values(values, "aspect_extraction")["all"] == 0.8
    assert decision_values(values, "sentiment")["laptops"] == 0.7
    assert decision_values(values, "overall_sentiment")["restaurants"] == 0.6


def test_missing_scope_is_reported_by_name() -> None:
    incomplete = report(0.8, 0.7, 0.6)
    del incomplete["results"]["restaurants"]
    with pytest.raises(ValueError, match="restaurants"):
        decision_values(incomplete, "sentiment")


def test_comparison_shows_each_verdict() -> None:
    text = render_comparison(
        report(0.70, 0.70, 0.70), report(0.80, 0.80, 0.80),
        deployed={"aspect_extraction", "sentiment"},
    )
    assert text.count("Verdict: **promote**") == 2
    assert "Verdict: **promote (nothing deployed)**" in text
    assert "joint backup (reference)" in text
    assert "macro-F1" in text and "span F1" in text


def make_model(folder: Path, marker: str, finished: bool = True) -> None:
    folder.mkdir(parents=True)
    (folder / "config.json").write_text(marker, encoding="utf-8")
    if finished:
        (folder / "training_log.json").write_text(f'{{"run": "{marker}"}}', encoding="utf-8")


def test_promote_archives_the_deployed_model_and_copies_the_candidate(tmp_path: Path) -> None:
    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    make_model(models / "sentiment", "old", finished=False)  # like today's model: no log
    make_model(candidates / "sentiment", "new")

    archive = promote("sentiment", models, candidates, "20261009-120000")

    assert archive == models / "previous" / "sentiment-20261009-120000"
    assert (archive / "config.json").read_text(encoding="utf-8") == "old"
    assert (models / "sentiment" / "config.json").read_text(encoding="utf-8") == "new"
    assert (models / "sentiment" / ".gitkeep").exists()
    assert (candidates / "sentiment" / "config.json").exists(), "candidate must be kept"


def test_promote_without_a_deployed_model_archives_nothing(tmp_path: Path) -> None:
    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    (models / "overall_sentiment").mkdir(parents=True)
    (models / "overall_sentiment" / ".gitkeep").write_text("", encoding="utf-8")
    make_model(candidates / "overall_sentiment", "new")

    assert promote("overall_sentiment", models, candidates, "20261009-120000") is None
    assert not (models / "previous").exists()
    assert (models / "overall_sentiment" / "config.json").read_text(encoding="utf-8") == "new"


def test_promote_refuses_an_unfinished_candidate(tmp_path: Path) -> None:
    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    make_model(models / "sentiment", "old")
    make_model(candidates / "sentiment", "new", finished=False)

    with pytest.raises(FileNotFoundError, match="training_log.json"):
        promote("sentiment", models, candidates, "20261009-120000")
    assert (models / "sentiment" / "config.json").read_text(encoding="utf-8") == "old"


def test_promoting_twice_changes_nothing(tmp_path: Path) -> None:
    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    make_model(models / "sentiment", "old")
    make_model(candidates / "sentiment", "new")
    promote("sentiment", models, candidates, "20261009-120000")

    assert promote("sentiment", models, candidates, "20261009-130000") is None
    assert [p.name for p in (models / "previous").iterdir()] == ["sentiment-20261009-120000"]
