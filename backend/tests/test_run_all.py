from __future__ import annotations

from pathlib import Path

from training.run_all import (
    CANDIDATES_DIR,
    LOCK_NAME,
    SMOKE_DIR,
    Step,
    build_steps,
    run,
    status,
)


class Recorder:
    """Stands in for running a step: records it and writes its completion marker."""

    def __init__(self, failing: str | None = None) -> None:
        self.failing = failing
        self.executed: list[str] = []

    def __call__(self, step: Step, log_path: Path) -> int:
        self.executed.append(step.name)
        if step.name == self.failing:
            return 1
        step.done_marker.parent.mkdir(parents=True, exist_ok=True)
        step.done_marker.write_text("{}", encoding="utf-8")
        return 0


def test_steps_are_in_training_then_evaluation_order(tmp_path: Path) -> None:
    assert [s.name for s in build_steps(tmp_path)] == [
        "aspect", "sentiment", "overall", "eval_candidate", "eval_current",
    ]


def test_real_steps_use_default_hyperparameters(tmp_path: Path) -> None:
    for step in build_steps(tmp_path):
        assert not {"--epochs", "--lr", "--limit", "--seed", "--batch-size"} & set(step.args)


def test_training_steps_write_only_inside_the_root(tmp_path: Path) -> None:
    for step in build_steps(tmp_path)[:3]:
        output_dir = Path(step.args[step.args.index("--output-dir") + 1])
        assert tmp_path in output_dir.parents
        assert step.done_marker == output_dir / "training_log.json"


def test_both_evaluations_cover_both_domains(tmp_path: Path) -> None:
    for step in build_steps(tmp_path)[3:]:
        position = step.args.index("--domains")
        assert step.args[position + 1 : position + 3] == ("laptops", "restaurants")
        assert tmp_path in step.done_marker.parents


def test_smoke_steps_are_small_and_skip_the_deployed_models(tmp_path: Path) -> None:
    steps = build_steps(tmp_path, smoke=True)
    assert [s.name for s in steps] == ["aspect", "sentiment", "overall", "eval_candidate"]
    for step in steps:
        assert step.args[step.args.index("--limit") + 1] == "32"
    for step in steps[:3]:
        assert step.args[step.args.index("--epochs") + 1] == "1"


def test_smoke_output_is_separate_from_real_candidates() -> None:
    assert CANDIDATES_DIR in SMOKE_DIR.parents
    assert SMOKE_DIR != CANDIDATES_DIR


def test_completed_steps_are_skipped(tmp_path: Path) -> None:
    steps = build_steps(tmp_path)
    steps[0].done_marker.parent.mkdir(parents=True)
    steps[0].done_marker.write_text("{}", encoding="utf-8")
    recorder = Recorder()
    assert run(steps, tmp_path / "logs", recorder) == 0
    assert recorder.executed == ["sentiment", "overall", "eval_candidate", "eval_current"]


def test_weights_without_training_log_are_not_complete(tmp_path: Path) -> None:
    steps = build_steps(tmp_path)
    (tmp_path / "sentiment").mkdir()
    (tmp_path / "sentiment" / "model.safetensors").write_bytes(b"partial")
    recorder = Recorder()
    run(steps, tmp_path / "logs", recorder)
    assert "sentiment" in recorder.executed


def test_run_stops_at_the_first_failing_step(tmp_path: Path) -> None:
    recorder = Recorder(failing="sentiment")
    assert run(build_steps(tmp_path), tmp_path / "logs", recorder) == 1
    assert recorder.executed == ["aspect", "sentiment"]


def test_step_that_succeeds_without_its_output_is_a_failure(tmp_path: Path) -> None:
    assert run(build_steps(tmp_path), tmp_path / "logs", lambda step, log: 0) == 1


def test_second_run_is_refused_while_a_lock_exists(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / LOCK_NAME).write_text("1234", encoding="utf-8")
    recorder = Recorder()
    assert run(build_steps(tmp_path), log_dir, recorder) == 2
    assert recorder.executed == []
    assert (log_dir / LOCK_NAME).exists(), "must not remove another run's lock"


def test_lock_is_removed_after_a_run(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    run(build_steps(tmp_path), log_dir, Recorder())
    assert not (log_dir / LOCK_NAME).exists()
    run(build_steps(tmp_path / "other"), log_dir, Recorder(failing="aspect"))
    assert not (log_dir / LOCK_NAME).exists()


def test_status_reports_done_running_and_pending(tmp_path: Path) -> None:
    steps = build_steps(tmp_path)
    log_dir = tmp_path / "logs"
    steps[0].done_marker.parent.mkdir(parents=True)
    steps[0].done_marker.write_text("{}", encoding="utf-8")
    assert status(steps, log_dir)[:2] == [("aspect", "done"), ("sentiment", "pending")]
    log_dir.mkdir()
    (log_dir / LOCK_NAME).write_text("1234", encoding="utf-8")
    assert status(steps, log_dir)[:3] == [
        ("aspect", "done"), ("sentiment", "running"), ("overall", "pending"),
    ]
