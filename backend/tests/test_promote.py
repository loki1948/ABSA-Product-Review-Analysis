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
    assert "not installed now (reference)" in text
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


# --- findings from the independent review -----------------------------------


def test_promote_archives_a_folder_that_is_not_just_the_placeholder(tmp_path: Path) -> None:
    """A model unzipped one level too deep has no top-level config.json; it must not be deleted."""
    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    nested = models / "sentiment" / "sentiment"
    nested.mkdir(parents=True)
    (nested / "model.safetensors").write_bytes(b"weights")
    make_model(candidates / "sentiment", "new")

    archive = promote("sentiment", models, candidates, "20261010-100000")

    assert archive is not None
    assert (archive / "sentiment" / "model.safetensors").read_bytes() == b"weights"
    assert (models / "sentiment" / "config.json").read_text(encoding="utf-8") == "new"


def test_half_copied_model_is_not_reported_as_installed(tmp_path: Path) -> None:
    """An interrupted copy can leave the training log without the weights."""
    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    make_model(candidates / "sentiment", "new")
    (candidates / "sentiment" / "model.safetensors").write_bytes(b"weights")
    (models / "sentiment").mkdir(parents=True)
    (models / "sentiment" / "training_log.json").write_bytes(
        (candidates / "sentiment" / "training_log.json").read_bytes()
    )

    promote("sentiment", models, candidates, "20261010-100000")

    assert (models / "sentiment" / "model.safetensors").read_bytes() == b"weights"
    assert not list(models.glob("*.incoming"))


def test_deployed_models_are_read_from_the_current_report(tmp_path: Path) -> None:
    from training.promote import deployed_models

    models = tmp_path / "models"
    for name in ("aspect_extraction", "sentiment", "overall_sentiment"):
        make_model(models / name, name)
    logs = {"aspect": {"run": "aspect_extraction"}, "sentiment": {"run": "sentiment"},
            "overall": {"run": "some other model"}}
    assert deployed_models({"training": logs}, models) == {"aspect_extraction", "sentiment"}
    logs["overall"] = {"run": "overall_sentiment"}
    assert deployed_models({"training": logs}, models) == {"aspect_extraction", "sentiment", "overall_sentiment"}
    assert deployed_models(None, models) == set()


def test_report_of_other_candidates_is_refused(tmp_path: Path) -> None:
    from training.promote import report_matches_models

    candidates = tmp_path / "candidates"
    for name in ("aspect_extraction", "sentiment", "overall_sentiment"):
        make_model(candidates / name, name)
    fresh = {"training": {"aspect": {"run": "aspect_extraction"}, "sentiment": {"run": "sentiment"},
                          "overall": {"run": "overall_sentiment"}}}
    assert report_matches_models(fresh, candidates)
    stale = {"training": {**fresh["training"], "sentiment": {"run": "an earlier candidate"}}}
    assert not report_matches_models(stale, candidates)


# --- findings from the second review ----------------------------------------


def _reports(tmp_path: Path, installed: dict[str, str], current_describes: dict[str, str] | None):
    """Folders plus the two reports; values are the 'run' marker of each model's log."""
    import json

    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    keys = {"aspect_extraction": "aspect", "sentiment": "sentiment", "overall_sentiment": "overall"}
    for name in keys:
        make_model(candidates / name, f"candidate-{name}")
        if name in installed:
            make_model(models / name, installed[name])
    candidate = report(0.8, 0.8, 0.8)
    candidate["training"] = {key: json.loads((candidates / name / "training_log.json").read_text())
                             for name, key in keys.items()}
    current = None
    if current_describes is not None:
        current = report(0.7, 0.7, 0.7)
        current["training"] = {keys[name]: {"run": run} for name, run in current_describes.items()}
    return models, candidates, candidate, current


def test_installed_model_that_was_never_evaluated_is_not_replaced_unseen(tmp_path: Path) -> None:
    """run_all stopped before evaluating the installed models: no comparison, so no automatic install."""
    from training.promote import decide

    models, candidates, candidate, _ = _reports(tmp_path, {"sentiment": "good-old-model"}, None)
    assert decide("sentiment", candidate, None, models, candidates).startswith("needs decision")
    assert decide("aspect_extraction", candidate, None, models, candidates) == "promote (nothing deployed)"


def test_stale_current_report_does_not_count_as_a_comparison(tmp_path: Path) -> None:
    from training.promote import decide

    models, candidates, candidate, current = _reports(
        tmp_path, {"sentiment": "restored-by-hand"}, {"sentiment": "some-earlier-model"})
    assert decide("sentiment", candidate, current, models, candidates).startswith("needs decision")


def test_evaluated_installed_model_is_compared(tmp_path: Path) -> None:
    from training.promote import decide

    models, candidates, candidate, current = _reports(tmp_path, {"sentiment": "old"}, {"sentiment": "old"})
    assert decide("sentiment", candidate, current, models, candidates) == "promote"


def test_candidate_that_is_already_installed_says_so_and_can_be_repaired(tmp_path: Path) -> None:
    from training.promote import decide

    models, candidates, candidate, current = _reports(tmp_path, {}, {"sentiment": "old"})
    (candidates / "sentiment" / "model.safetensors").write_bytes(b"weights")
    promote("sentiment", models, candidates, "20261010-100000")
    assert decide("sentiment", candidate, current, models, candidates) == "already installed"

    (models / "sentiment" / "model.safetensors").write_bytes(b"cut")  # damaged copy
    promote("sentiment", models, candidates, "20261010-110000")
    assert (models / "sentiment" / "model.safetensors").read_bytes() == b"weights"


def test_model_in_use_is_left_intact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The backend holds the weights open: the installed model must stay complete."""
    import os

    models, candidates = tmp_path / "models", tmp_path / "models" / "candidates"
    make_model(models / "sentiment", "old")
    make_model(candidates / "sentiment", "new")

    def locked(source, target):
        raise PermissionError("file in use")

    monkeypatch.setattr(os, "rename", locked)
    with pytest.raises(RuntimeError, match="in use"):
        promote("sentiment", models, candidates, "20261010-100000")
    assert (models / "sentiment" / "config.json").read_text(encoding="utf-8") == "old"
    assert (models / "sentiment" / "training_log.json").exists()
    assert not (models / "sentiment.incoming").exists()
    assert not (models / "previous").exists()
