from __future__ import annotations

from pathlib import Path

import pytest

from training.run_all import (
    CANDIDATES_DIR,
    LOCK_NAME,
    SMOKE_DIR,
    Step,
    build_steps,
    run,
    status,
)


@pytest.fixture(autouse=True)
def installed_models(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Three stand-in installed models, so the chain includes ``eval_current`` on any machine."""
    import json

    import training.run_all as run_all_module

    root = tmp_path_factory.mktemp("installed")
    for folder in ("aspect_extraction", "sentiment", "overall_sentiment"):
        (root / folder).mkdir()
        (root / folder / "config.json").write_text("{}", encoding="utf-8")
        (root / folder / "training_log.json").write_text(json.dumps({"run": folder}), encoding="utf-8")
    monkeypatch.setattr(run_all_module, "DEPLOYED_ROOT", root)
    return root


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
    (log_dir / LOCK_NAME).write_text("not a process id", encoding="utf-8")
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


def test_keep_awake_also_keeps_the_display_on() -> None:
    # On laptops with Modern Standby, the display switching off after the idle
    # timeout puts the machine to sleep even while "system required" is set.
    from training.run_all import AWAKE_FLAGS

    es_continuous, es_system_required, es_display_required = 0x80000000, 0x1, 0x2
    assert AWAKE_FLAGS == es_continuous | es_system_required | es_display_required


# --- findings from the independent review -----------------------------------


def _model(folder: Path, run: str) -> None:
    import json

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.json").write_text("{}", encoding="utf-8")
    (folder / "training_log.json").write_text(json.dumps({"run": run}), encoding="utf-8")


def test_evaluation_of_a_replaced_candidate_is_not_complete(tmp_path: Path) -> None:
    import json

    from training.run_all import is_done

    for name in ("aspect_extraction", "sentiment", "overall_sentiment"):
        _model(tmp_path / name, "first")
    step = build_steps(tmp_path)[3]
    step.done_marker.parent.mkdir(parents=True)
    logs = {"aspect": {"run": "first"}, "sentiment": {"run": "first"}, "overall": {"run": "first"}}
    step.done_marker.write_text(json.dumps({"training": logs}), encoding="utf-8")
    assert is_done(step)

    _model(tmp_path / "sentiment", "retrained")
    assert not is_done(step), "the report describes the earlier sentiment candidate"


def test_fresh_clone_has_no_current_models_to_evaluate(tmp_path: Path) -> None:
    deployed = tmp_path / "deployed"
    steps = build_steps(tmp_path / "candidates", deployed_root=deployed)
    assert [s.name for s in steps] == ["aspect", "sentiment", "overall", "eval_candidate"]


def test_current_evaluation_uses_the_deployed_overall_model_when_there_is_one(tmp_path: Path) -> None:
    deployed = tmp_path / "deployed"
    for name in ("aspect_extraction", "sentiment", "overall_sentiment"):
        _model(deployed / name, name)
    step = build_steps(tmp_path / "candidates", deployed_root=deployed)[4]
    overall = step.args[step.args.index("--overall-model-dir") + 1]
    assert Path(overall) == deployed / "overall_sentiment"


def test_lock_of_a_dead_process_is_taken_over(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / LOCK_NAME).write_text("999999999", encoding="utf-8")  # no such process
    recorder = Recorder()
    assert run(build_steps(tmp_path, deployed_root=tmp_path / "none"), log_dir, recorder) == 0
    assert recorder.executed[0] == "aspect"


def test_lock_of_a_live_process_is_respected(tmp_path: Path) -> None:
    import os

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / LOCK_NAME).write_text(str(os.getpid()), encoding="utf-8")
    recorder = Recorder()
    assert run(build_steps(tmp_path), log_dir, recorder) == 2
    assert recorder.executed == []


def test_lock_is_respected_while_the_training_child_is_alive(tmp_path: Path) -> None:
    """The parent was killed but its training process still runs: no second training."""
    import os

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / LOCK_NAME).write_text(f"999999999\n{os.getpid()}", encoding="utf-8")
    recorder = Recorder()
    assert run(build_steps(tmp_path), log_dir, recorder) == 2
    assert recorder.executed == []


def test_lock_naming_two_dead_processes_is_taken_over(tmp_path: Path) -> None:
    """Third review: a lock with both a parent and a child id, both gone, is stale."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / LOCK_NAME).write_text("999999999\n999999998", encoding="utf-8")
    recorder = Recorder()
    assert run(build_steps(tmp_path), log_dir, recorder) == 0
    assert recorder.executed[0] == "aspect"


def test_lock_names_the_training_child_while_it_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    import training.run_all as run_all_module
    from training.run_all import execute_step

    lock = tmp_path / LOCK_NAME
    lock.write_text(str(os.getpid()), encoding="utf-8")
    seen: list[str] = []

    class Child:
        pid = 4242

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def wait(self) -> int:
            seen.append(lock.read_text(encoding="utf-8"))
            return 0

    monkeypatch.setattr(run_all_module.subprocess, "Popen", Child)
    step = Step("aspect", "training.train_aspect", (), tmp_path / "done")
    assert execute_step(step, tmp_path / "aspect.log", lock) == 0
    assert seen == [f"{os.getpid()}\n4242"]
    assert lock.read_text(encoding="utf-8") == str(os.getpid())
