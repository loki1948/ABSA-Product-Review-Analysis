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
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.paths import MODELS_DIR
from training.run_all import CANDIDATES_DIR, MODEL_FOLDERS, read_log

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
        column = "deployed" if is_deployed else "not installed now (reference)"
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


def report_matches_models(report: dict[str, Any], root: Path) -> bool:
    """True when ``report`` was computed from the models now in ``root``."""
    training = report.get("training", {})
    return all(training.get(key) == read_log(root / folder) for key, folder in MODEL_FOLDERS.items())


def deployed_models(current_report: dict[str, Any] | None, models_dir: Path) -> set[str]:
    """Installed models that ``current_report`` actually describes.

    Only these can be compared with a candidate. A slot that was evaluated with
    a stand-in (or not at all) counts as "nothing deployed".
    """
    if current_report is None:
        return set()
    training = current_report.get("training", {})
    return {
        folder for key, folder in MODEL_FOLDERS.items()
        if (models_dir / folder / "config.json").exists()
        and training.get(key) == read_log(models_dir / folder)
    }


def decide(
    name: str,
    candidate_report: dict[str, Any],
    current_report: dict[str, Any] | None,
    models_dir: Path,
    candidates_dir: Path,
) -> str:
    """The verdict for one model slot.

    ``promote`` / ``promote (nothing deployed)``  install the candidate
    ``already installed``                         the candidate is the installed model
    ``needs decision ...``                        a person has to judge
    """
    installed = models_dir / name
    candidate_log = read_log(candidates_dir / name)
    has_model = installed.exists() and not {item.name for item in installed.iterdir()} <= {".gitkeep"}
    if has_model and candidate_log and read_log(installed) == candidate_log:
        return "already installed"
    if not has_model:
        return "promote (nothing deployed)"
    if name not in deployed_models(current_report, models_dir):
        # Something is installed, but no evaluation of it exists (run_all was
        # interrupted, or the folder was changed by hand). Installing over it
        # would skip the comparison this script exists for.
        if not (installed / "training_log.json").exists():
            return ("needs decision (the installed model has no training_log.json, so it cannot be "
                    "identified; restore the folder from models/previous or absa-models.zip, "
                    "or move it away to install the candidate)")
        if not all((models_dir / folder / "config.json").exists() for folder in MODELS):
            # run_all evaluates the installed models only when all three are there.
            return ("needs decision (the installed model was not evaluated; run "
                    "`python -m training.promote --apply` to fill the empty slots first, "
                    "then `python -m training.run_all` to evaluate it)")
        return ("needs decision (the installed model was not evaluated; "
                "run `python -m training.run_all` to evaluate it)")
    return verdict(decision_values(current_report, name), decision_values(candidate_report, name))


def _same_files(source: Path, target: Path) -> bool:
    """Every file of ``source`` exists in ``target`` with the same size."""
    return all(
        (target / item.name).is_file() and (target / item.name).stat().st_size == item.stat().st_size
        for item in source.iterdir() if item.is_file()
    )


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
    if (
        target_log.exists()
        and target_log.read_bytes() == candidate_log.read_bytes()
        and _same_files(candidate, target)
    ):
        logger.info("%s: this candidate is already installed", name)
        return None

    # Copy next to the target first and rename at the end: an interrupted copy
    # then leaves a stray "<name>.incoming" folder, never a half-installed model.
    incoming = models_dir / f"{name}.incoming"
    if incoming.exists():
        shutil.rmtree(incoming)
    shutil.copytree(candidate, incoming)
    (incoming / ".gitkeep").touch()

    archive: Path | None = None
    if target.exists():
        if {item.name for item in target.iterdir()} <= {".gitkeep"}:
            shutil.rmtree(target)  # only the placeholder: nothing to keep
        else:
            # A model, or anything else someone put here: keep it. A plain
            # rename either moves the whole folder or changes nothing; a
            # copy-and-delete could stop halfway and leave a broken model.
            archive = models_dir / "previous" / f"{name}-{stamp}"
            archive.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.rename(target, archive)
            except OSError as exc:
                shutil.rmtree(incoming, ignore_errors=True)
                try:
                    archive.parent.rmdir()  # only if this call created it and it is still empty
                except OSError:
                    pass
                raise RuntimeError(
                    f"{target} is in use, so it was left as it is. Stop the backend "
                    f"(it keeps the model files open) and run this again."
                ) from exc
    os.replace(incoming, target)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="install the candidates that qualify")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    reports: dict[str, dict[str, Any] | None] = {}
    for which in ("current", "candidate"):
        path = CANDIDATES_DIR / "eval" / which / "evaluation_report.json"
        reports[which] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    candidate_report, current_report = reports["candidate"], reports["current"]
    if candidate_report is None:
        logger.error("No candidate evaluation found. Run: python -m training.run_all")
        return 1
    if not report_matches_models(candidate_report, CANDIDATES_DIR):
        logger.error("The candidate evaluation describes other models than those in %s "
                     "(one was retrained since). Run: python -m training.run_all", CANDIDATES_DIR)
        return 1

    # A model is compared only if the "current" evaluation really is of the
    # model installed now; otherwise there is nothing valid to compare with.
    deployed = deployed_models(current_report, MODELS_DIR)
    if current_report is None:
        print("No evaluation of installed models was found.\n")
    else:
        print(render_comparison(current_report, candidate_report, deployed))

    verdicts = {
        name: decide(name, candidate_report, current_report, MODELS_DIR, CANDIDATES_DIR) for name in MODELS
    }
    print("Decision per model:")
    for name, value in verdicts.items():
        print(f"  {name}: {value}")
    undecided = [name for name, value in verdicts.items() if value.startswith("needs decision")]
    failed = []
    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        for name, value in verdicts.items():
            if value != "already installed" and not value.startswith("promote"):
                logger.warning("%s: not installed (%s)", name, value)
                continue
            try:
                archive = promote(name, MODELS_DIR, CANDIDATES_DIR, stamp)
            except RuntimeError as exc:  # the model is in use; the other slots still go ahead
                logger.error("%s: %s", name, exc)
                failed.append(name)
                continue
            if value == "already installed":
                # promote() re-copies an incomplete installed copy.
                if archive:
                    logger.info("%s: the installed copy was incomplete and has been copied again; "
                                "the incomplete copy was moved to %s", name, archive)
                else:
                    logger.info("%s: already installed and complete", name)
            else:
                logger.info("%s: installed%s", name, f"; previous model moved to {archive}" if archive else "")
    if failed:
        return 4
    return 3 if undecided else 0


if __name__ == "__main__":
    sys.exit(main())
