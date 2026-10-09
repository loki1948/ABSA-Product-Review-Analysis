"""Compare the candidate models with the deployed ones and install the better ones.

Run from the ``backend`` directory, after ``python -m training.run_all``:

    python -m training.promote            # print the comparison only
    python -m training.promote --apply    # also install the candidates that qualify

Both sets of models were evaluated by ``run_all`` on the laptops and the
restaurants test sets. One metric decides per model: span F1 for aspect
extraction, macro-F1 for the two sentiment models (the classes are imbalanced,
so accuracy alone would reward ignoring the neutral class).

A candidate is installed when its decision metric is higher on both domains
together and not more than ``TOLERANCE`` lower on either single domain.
Anything else is reported as "needs decision" and left for a person to judge.

Nothing is deleted: the model being replaced is moved to ``models/previous``,
and the candidate folder is copied, not moved.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.paths import MODELS_DIR
from training.run_all import CANDIDATES_DIR

logger = logging.getLogger("promote")

TOLERANCE = 0.01
SCOPES = ("all", "laptops", "restaurants")

# Model folder -> (title, name of the decision metric, path to it inside one
# scope of the evaluation report, other metrics shown for context).
MODELS: dict[str, tuple[str, str, tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]] = {
    "aspect_extraction": (
        "Aspect extraction", "span F1", ("aspect_extraction", "f1"),
        (("precision", ("aspect_extraction", "precision")),
         ("recall", ("aspect_extraction", "recall")),
         ("end-to-end F1", ("end_to_end", "f1"))),
    ),
    "sentiment": (
        "Aspect sentiment", "macro-F1", ("aspect_sentiment", "macro", "f1"),
        (("accuracy", ("aspect_sentiment", "accuracy")),
         ("accuracy on mixed sentences", ("aspect_sentiment_by_sentence_type", "mixed", "accuracy"))),
    ),
    "overall_sentiment": (
        "Overall sentiment", "macro-F1", ("overall_sentiment", "macro", "f1"),
        (("accuracy", ("overall_sentiment", "accuracy")),),
    ),
}


def _lookup(results: dict[str, Any], path: tuple[str, ...]) -> float | None:
    value: Any = results
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def decision_values(report: dict[str, Any], model: str) -> dict[str, float]:
    """The decision metric of ``model`` for every scope of an evaluation report."""
    path = MODELS[model][2]
    values: dict[str, float] = {}
    for scope in SCOPES:
        if scope not in report["results"]:
            raise ValueError(f"report has no results for scope '{scope}'")
        value = _lookup(report["results"][scope], path)
        if value is None:
            raise ValueError(f"report has no {'.'.join(path)} for scope '{scope}'")
        values[scope] = value
    return values


def verdict(current: dict[str, float] | None, candidate: dict[str, float]) -> str:
    """``current`` is None when no model is deployed in that slot."""
    if current is None:
        return "promote (nothing deployed)"
    better_overall = candidate["all"] > current["all"]
    no_domain_drops = all(
        candidate[scope] >= current[scope] - TOLERANCE for scope in SCOPES if scope != "all"
    )
    return "promote" if better_overall and no_domain_drops else "needs decision"


def _cell(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def render_comparison(
    current_report: dict[str, Any], candidate_report: dict[str, Any], deployed: set[str]
) -> str:
    """Markdown tables: deployed vs. candidate, per model, metric and test domain."""
    lines: list[str] = []
    for model, (title, metric_name, path, extras) in MODELS.items():
        is_deployed = model in deployed
        current = decision_values(current_report, model)
        candidate = decision_values(candidate_report, model)
        column = "deployed" if is_deployed else "joint backup (reference)"
        lines += [
            f"## {title}",
            "",
            f"Decision metric: {metric_name}.",
            "",
            f"| Metric | Test set | {column} | candidate | difference |",
            "|---|---|---|---|---|",
        ]
        for name, metric_path in ((metric_name, path), *extras):
            for scope in SCOPES:
                old = _lookup(current_report["results"][scope], metric_path)
                new = _lookup(candidate_report["results"][scope], metric_path)
                diff = "n/a" if old is None or new is None else f"{new - old:+.4f}"
                lines.append(f"| {name} | {scope} | {_cell(old)} | {_cell(new)} | {diff} |")
        lines += ["", f"Verdict: **{verdict(current if is_deployed else None, candidate)}**", ""]
    return "\n".join(lines)


def promote(name: str, models_dir: Path, candidates_dir: Path, stamp: str) -> Path | None:
    """Install ``candidates_dir/name`` as ``models_dir/name``.

    The model it replaces is moved to ``models_dir/previous/<name>-<stamp>``;
    that path is returned, or None when there was nothing to archive.
    """
    candidate, target = candidates_dir / name, models_dir / name
    candidate_log = candidate / "training_log.json"
    if not candidate_log.exists():
        raise FileNotFoundError(f"{candidate_log} not found: the candidate did not finish training")

    target_log = target / "training_log.json"
    if target_log.exists() and target_log.read_bytes() == candidate_log.read_bytes():
        logger.info("%s: this candidate is already installed", name)
        return None

    archive: Path | None = None
    if (target / "config.json").exists():
        archive = models_dir / "previous" / f"{name}-{stamp}"
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(archive))
    elif target.exists():
        shutil.rmtree(target)  # holds only the .gitkeep placeholder
    shutil.copytree(candidate, target)
    (target / ".gitkeep").touch()
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="install the candidates that qualify")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    reports = {}
    for which in ("current", "candidate"):
        path = CANDIDATES_DIR / "eval" / which / "evaluation_report.json"
        if not path.exists():
            logger.error("%s not found. Run: python -m training.run_all", path)
            return 1
        reports[which] = json.loads(path.read_text(encoding="utf-8"))

    deployed = {
        name for name in MODELS
        # eval_current used the joint backup in the overall slot, so that slot
        # only counts as deployed if a candidate has since been installed there.
        if (MODELS_DIR / name / "config.json").exists() and name != "overall_sentiment"
    }
    print(render_comparison(reports["current"], reports["candidate"], deployed))

    verdicts = {
        name: verdict(
            decision_values(reports["current"], name) if name in deployed else None,
            decision_values(reports["candidate"], name),
        )
        for name in MODELS
    }
    undecided = [name for name, value in verdicts.items() if value == "needs decision"]
    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        for name, value in verdicts.items():
            if not value.startswith("promote"):
                logger.warning("%s: not installed (%s)", name, value)
                continue
            archive = promote(name, MODELS_DIR, CANDIDATES_DIR, stamp)
            logger.info("%s: installed%s", name, f"; previous model moved to {archive}" if archive else "")
    return 3 if undecided else 0


if __name__ == "__main__":
    sys.exit(main())
