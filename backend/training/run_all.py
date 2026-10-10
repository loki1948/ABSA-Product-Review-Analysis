"""Train the three models and evaluate them, one step after another.

Run from the ``backend`` directory:

    python -m training.run_all            # full run, several hours on a CPU
    python -m training.run_all --smoke    # same chain on 32 sentences, minutes
    python -m training.run_all --status   # what is done, running, pending

Nothing here touches the deployed models. Everything is written to
``models/candidates``; ``python -m training.promote`` installs the result once
it has been compared with what is deployed.

The run can be interrupted. A step is complete when the file it ends with
exists (``training_log.json`` for training, the report for evaluation), and
complete steps are skipped, so starting the script again continues with the
first unfinished step. A training step that was interrupted starts over.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from app.paths import ASPECT_MODEL_DIR, BACKEND_DIR, MODELS_DIR, SENTIMENT_MODEL_DIR

logger = logging.getLogger("run_all")

CANDIDATES_DIR: Path = MODELS_DIR / "candidates"
SMOKE_DIR: Path = CANDIDATES_DIR / "_smoke"
LOCK_NAME = "run_all.lock"
EVAL_DOMAINS = ("laptops", "restaurants")
# No overall-sentiment model was deployed before the two-domain retrain; the
# earlier joint model fills that slot when the deployed models are evaluated.
CURRENT_OVERALL_DIR: Path = MODELS_DIR / "sentiment_joint_backup"


@dataclass(frozen=True)
class Step:
    name: str
    module: str
    args: tuple[str, ...]
    done_marker: Path


def _evaluation(name: str, out_dir: Path, aspect: Path, sentiment: Path, overall: Path) -> Step:
    report = out_dir / "evaluation_report.json"
    return Step(
        name,
        "training.evaluate",
        (
            "--aspect-model-dir", str(aspect),
            "--sentiment-model-dir", str(sentiment),
            "--overall-model-dir", str(overall),
            "--domains", *EVAL_DOMAINS,
            "--report", str(report),
            "--markdown", str(out_dir / "results.md"),
        ),
        report,
    )


def build_steps(root: Path, smoke: bool = False) -> list[Step]:
    """The chain, in execution order. ``smoke`` shrinks it to a quick check."""
    aspect, sentiment, overall = root / "aspect_extraction", root / "sentiment", root / "overall_sentiment"
    steps = [
        Step("aspect", "training.train_aspect",
             ("--output-dir", str(aspect)), aspect / "training_log.json"),
        Step("sentiment", "training.train_sentiment",
             ("--task", "aspect", "--output-dir", str(sentiment)), sentiment / "training_log.json"),
        Step("overall", "training.train_sentiment",
             ("--task", "overall", "--output-dir", str(overall)), overall / "training_log.json"),
        _evaluation("eval_candidate", root / "eval" / "candidate", aspect, sentiment, overall),
        _evaluation("eval_current", root / "eval" / "current",
                    ASPECT_MODEL_DIR, SENTIMENT_MODEL_DIR, CURRENT_OVERALL_DIR),
    ]
    if not smoke:
        return steps
    small = []
    for step in steps[:4]:
        extra = ("--limit", "32") if step.name.startswith("eval") else ("--limit", "32", "--epochs", "1")
        small.append(Step(step.name, step.module, step.args + extra, step.done_marker))
    return small


def execute_step(step: Step, log_path: Path) -> int:
    """Run one step as a child process; its output goes to ``log_path``."""
    with log_path.open("w", encoding="utf-8") as log:
        return subprocess.run(
            [sys.executable, "-m", step.module, *step.args],
            cwd=BACKEND_DIR, stdout=log, stderr=subprocess.STDOUT,
        ).returncode


def run(
    steps: list[Step], log_dir: Path, execute: Callable[[Step, Path], int] = execute_step
) -> int:
    """Run the unfinished steps in order. Returns 0, or the first failure's exit code."""
    log_dir.mkdir(parents=True, exist_ok=True)
    lock = log_dir / LOCK_NAME
    try:
        # "x" fails if the file exists: two trainings must never share the CPU.
        with lock.open("x", encoding="utf-8") as handle:
            handle.write("run_all is active\n")
    except FileExistsError:
        logger.error("Another run is active (or was killed): %s. "
                     "If no training is running, delete that file and start again.", lock)
        return 2
    try:
        for step in steps:
            if step.done_marker.exists():
                logger.info("%s: already complete, skipped", step.name)
                continue
            logger.info("%s: started (log: %s)", step.name, log_dir / f"{step.name}.log")
            code = execute(step, log_dir / f"{step.name}.log")
            if code != 0:
                logger.error("%s: failed with exit code %d", step.name, code)
                return code
            if not step.done_marker.exists():
                logger.error("%s: finished but did not write %s", step.name, step.done_marker)
                return 1
            logger.info("%s: complete", step.name)
        return 0
    finally:
        lock.unlink(missing_ok=True)


def status(steps: list[Step], log_dir: Path) -> list[tuple[str, str]]:
    """(step, "done" | "running" | "pending") for every step."""
    active = (log_dir / LOCK_NAME).exists()
    result: list[tuple[str, str]] = []
    for step in steps:
        if step.done_marker.exists():
            result.append((step.name, "done"))
        elif active:
            result.append((step.name, "running"))
            active = False
        else:
            result.append((step.name, "pending"))
    return result


# ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED. The display flag
# matters: on laptops with Modern Standby the screen switching off after the
# idle timeout suspends the machine even while "system required" is set (this
# froze a run for hours).
AWAKE_FLAGS = 0x80000000 | 0x00000001 | 0x00000002
_ES_CONTINUOUS = 0x80000000


@contextmanager
def keep_awake() -> Iterator[None]:
    """Keep Windows and its display awake while training runs.

    Closing the lid or pressing the power button still suspends the machine.
    """
    if sys.platform != "win32":
        yield
        return
    import ctypes

    ctypes.windll.kernel32.SetThreadExecutionState(AWAKE_FLAGS)
    try:
        yield
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)


def _last_line(path: Path) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    return lines[-1] if lines else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--smoke", action="store_true", help="quick check on 32 sentences")
    parser.add_argument("--status", action="store_true", help="show progress and exit")
    args = parser.parse_args()

    root = SMOKE_DIR if args.smoke else CANDIDATES_DIR
    log_dir = root / "logs"
    steps = build_steps(root, args.smoke)

    if args.status:
        for name, state in status(steps, log_dir):
            detail = _last_line(log_dir / f"{name}.log") if state == "running" else ""
            print(f"{name:15s} {state:8s} {detail}")
        return 0

    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(log_dir / "run_all.log", encoding="utf-8")],
    )
    with keep_awake():
        return run(steps, log_dir)


if __name__ == "__main__":
    sys.exit(main())
