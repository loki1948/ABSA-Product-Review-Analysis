# Models and Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train the three BERT models on both domains without touching the deployed ones, promote them after a two-domain comparison, and regenerate every result file and test from the promoted models.

**Architecture:** A resumable runner (`training/run_all.py`) executes the existing training and evaluation scripts one after another into `models/candidates/`. A separate script (`training/promote.py`) compares the candidate report with the deployed-model report and, on request, archives the deployed model and copies the candidate in. The existing `training/evaluate.py` then rewrites the published results.

**Tech Stack:** Python 3.10+, PyTorch (CPU), Hugging Face Transformers, pytest, FastAPI TestClient. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-09-models-evaluation-design.md`

## Global Constraints

- Run every command from `backend/` with `..\.venv\Scripts\python.exe`.
- Training hyperparameters are the scripts' defaults. Do not pass `--epochs`, `--lr`, `--batch-size`, `--seed` or `--domains` to the real runs.
- Training output goes only to `models/candidates/`. Nothing writes to `models/aspect_extraction`, `models/sentiment` or `models/overall_sentiment` before Task 7.
- Never delete or modify `models/sentiment_joint_backup/`, `models/train_sentiment_aspect.log`, `models/previous/` or `models/candidates/` (except `models/candidates/_smoke/`).
- One training process at a time.
- No metric is typed by hand anywhere. Numbers in docs come from `training/evaluate.py` output.
- Python style of the repo: type hints on every function, `logging` instead of `print` in library code, docstring where the purpose is not obvious.
- Promotion tolerance is `0.01`. Smoke test uses `--limit 32 --epochs 1`.
- Commits happen only if the user has approved committing (Task 0). If not, skip every "Commit" step.

## Review Focus

1. A candidate folder that holds weights but no `training_log.json` (a run killed after an epoch's checkpoint): the runner must treat the step as incomplete and retrain it. Test in Task 1.
2. The runner is launched while another run is active: it must refuse, not start a second training. Test in Task 1.
3. `promote --apply` is run twice: the second run must change nothing, not archive the model it just promoted. Test in Task 2.
4. The two reports cover different scopes (for example one lacks `restaurants`): comparison must fail with a message naming the missing scope, not a `KeyError`. Test in Task 2.
5. Smoke-test output must never mark a real step complete: smoke steps live under `_smoke/`. Test in Task 1.

---

### Task 0: Baseline commit (only with the user's approval)

**Files:** none changed.

- [ ] **Step 1:** Confirm `git status --short` lists only untracked files and that `models/*/` weights, `data/raw`, `data/processed`, `.venv` and `node_modules` are ignored (`git status --short --ignored | grep model.safetensors` shows them as `!!`).
- [ ] **Step 2:** `git add -A && git commit -m "Initial commit: ABSA backend, training scripts, frontend scaffold, docs"`.
- [ ] **Step 3:** `git switch -c feature/models-evaluation`.

### Task 1: Resumable training runner

**Files:**
- Create: `backend/training/run_all.py`
- Test: `backend/tests/test_run_all.py`

**Interfaces:**
- Produces:
  - `Step` — frozen dataclass: `name: str`, `module: str`, `args: tuple[str, ...]`, `done_marker: Path`.
  - `build_steps(root: Path, smoke: bool = False) -> list[Step]`
  - `run(steps: list[Step], log_dir: Path, execute: Callable[[Step, Path], int] = execute_step) -> int`
  - `status(steps: list[Step], log_dir: Path) -> list[tuple[str, str]]` — `(step name, "done" | "running" | "pending")`.
  - CLI: `python -m training.run_all [--smoke] [--status]`.
  - Constants: `CANDIDATES_DIR = MODELS_DIR / "candidates"`, `SMOKE_DIR = CANDIDATES_DIR / "_smoke"`, `LOCK_NAME = "run_all.lock"`.

Step table that `build_steps(root)` must return, in this order:

| name | module | args | done_marker |
|---|---|---|---|
| `aspect` | `training.train_aspect` | `--output-dir <root>/aspect_extraction` | `<root>/aspect_extraction/training_log.json` |
| `sentiment` | `training.train_sentiment` | `--task aspect --output-dir <root>/sentiment` | `<root>/sentiment/training_log.json` |
| `overall` | `training.train_sentiment` | `--task overall --output-dir <root>/overall_sentiment` | `<root>/overall_sentiment/training_log.json` |
| `eval_candidate` | `training.evaluate` | the three `--*-model-dir` flags pointing into `<root>`, `--domains laptops restaurants`, `--report <root>/eval/candidate/evaluation_report.json`, `--markdown <root>/eval/candidate/results.md` | that report |
| `eval_current` | `training.evaluate` | `--aspect-model-dir models/aspect_extraction --sentiment-model-dir models/sentiment --overall-model-dir models/sentiment_joint_backup --domains laptops restaurants --report <root>/eval/current/evaluation_report.json --markdown <root>/eval/current/results.md` | that report |

With `smoke=True`: the three training steps get `--limit 32 --epochs 1` appended, `eval_candidate` gets `--limit 32`, and `eval_current` is omitted.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_run_all.py`. Each uses `tmp_path` as `root` and a fake `execute` that records step names and returns a chosen exit code.

```python
def test_steps_are_in_training_then_evaluation_order(tmp_path):
    assert [s.name for s in build_steps(tmp_path)] == [
        "aspect", "sentiment", "overall", "eval_candidate", "eval_current"]

def test_real_steps_use_default_hyperparameters(tmp_path):
    for step in build_steps(tmp_path):
        assert not {"--epochs", "--lr", "--limit", "--seed"} & set(step.args)

def test_smoke_steps_are_small_and_skip_the_deployed_models(tmp_path):
    steps = build_steps(tmp_path, smoke=True)
    assert [s.name for s in steps] == ["aspect", "sentiment", "overall", "eval_candidate"]
    assert all("32" in s.args for s in steps)

def test_completed_steps_are_skipped(tmp_path):
    # create aspect's done_marker, run with a recording execute -> "aspect" not executed

def test_weights_without_training_log_are_not_complete(tmp_path):
    # create <root>/sentiment/model.safetensors only -> "sentiment" IS executed

def test_run_stops_at_the_first_failing_step(tmp_path):
    # execute returns 1 for "sentiment" -> run() == 1, "overall" never executed

def test_second_run_is_refused_while_a_lock_exists(tmp_path):
    # create log_dir / LOCK_NAME -> run() == 2 and nothing executed

def test_lock_is_removed_after_a_run(tmp_path):
    # after run() returns (success or failure) the lock file does not exist

def test_status_reports_done_and_pending(tmp_path):
    # aspect marker present -> [("aspect", "done"), ("sentiment", "pending"), ...]
```

Also assert, for review-focus item 5, that `SMOKE_DIR` is inside `CANDIDATES_DIR` and differs from it.

- [ ] **Step 2:** Run `..\.venv\Scripts\python.exe -m pytest tests/test_run_all.py -q`. Expected: import error, `training.run_all` does not exist.
- [ ] **Step 3: Implement `run_all.py`.**
  - `execute_step(step, log_path) -> int`: `subprocess.run([sys.executable, "-m", step.module, *step.args], cwd=<backend dir>, stdout=<log file>, stderr=subprocess.STDOUT)`, return code returned.
  - `run`: create `log_dir`; if the lock exists return `2` with a logged message naming the lock path; otherwise create it, and in a `try/finally` remove it. For each step: skip when `done_marker.exists()`, else execute with log `log_dir / f"{step.name}.log"`; on non-zero return that code. A step that returns 0 but leaves no marker is a failure (return `1`).
  - `status`: "running" for the first step that is not done while the lock exists.
  - `keep_awake()` context manager used by `main`: on `sys.platform == "win32"` call `ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)` on entry and `(0x80000000)` on exit; elsewhere do nothing.
  - `main`: `--smoke` selects `SMOKE_DIR` as root, otherwise `CANDIDATES_DIR`; `log_dir = root / "logs"`; `--status` prints the status table and the last line of the running step's log, then exits 0. Progress lines also go to `log_dir / "run_all.log"`.
- [ ] **Step 4:** Run the test file again. Expected: all pass.
- [ ] **Step 5:** Commit `feat(training): resumable run_all chain that trains into models/candidates`.

### Task 2: Comparison and promotion

**Files:**
- Create: `backend/training/promote.py`
- Test: `backend/tests/test_promote.py`

**Interfaces:**
- Consumes: report layout written by `training/evaluate.py`: `report["results"][scope]` with `aspect_extraction.{precision,recall,f1}`, `end_to_end.f1`, `aspect_sentiment.accuracy`, `aspect_sentiment.macro.f1`, `aspect_sentiment_by_sentence_type.mixed.accuracy`, `overall_sentiment.accuracy`, `overall_sentiment.macro.f1`; scopes `all`, `laptops`, `restaurants`.
- Produces:
  - `TOLERANCE = 0.01`, `SCOPES = ("all", "laptops", "restaurants")`
  - `MODELS = {"aspect_extraction": ("aspect_extraction", "f1"), "sentiment": ("aspect_sentiment", "macro", "f1"), "overall_sentiment": ("overall_sentiment", "macro", "f1")}` — folder name to decision-metric path.
  - `decision_values(report: dict, model: str) -> dict[str, float]` — scope to value; raises `ValueError("report has no results for scope 'restaurants'")` when a scope is missing.
  - `verdict(current: dict[str, float] | None, candidate: dict[str, float]) -> str` — returns `"promote"`, `"needs decision"` or `"promote (nothing deployed)"`.
  - `render_comparison(current_report: dict, candidate_report: dict, deployed: set[str]) -> str` — markdown tables per spec section 4.3.
  - `promote(name: str, models_dir: Path, candidates_dir: Path, stamp: str) -> Path | None` — returns the archive path, or `None` when nothing was archived.
  - CLI: `python -m training.promote [--apply]`; without `--apply` it only prints.

- [ ] **Step 1: Write the failing tests.**

```python
def test_higher_everywhere_is_promoted():
    assert verdict({"all": .70, "laptops": .79, "restaurants": .55},
                   {"all": .82, "laptops": .80, "restaurants": .84}) == "promote"

def test_small_drop_on_one_domain_is_tolerated():
    assert verdict({"all": .70, "laptops": .790, "restaurants": .55},
                   {"all": .82, "laptops": .781, "restaurants": .84}) == "promote"

def test_larger_drop_on_one_domain_needs_a_decision():
    assert verdict({"all": .70, "laptops": .79, "restaurants": .55},
                   {"all": .82, "laptops": .77, "restaurants": .84}) == "needs decision"

def test_not_better_overall_needs_a_decision():
    assert verdict({"all": .82, "laptops": .80, "restaurants": .84},
                   {"all": .82, "laptops": .80, "restaurants": .84}) == "needs decision"

def test_model_with_nothing_deployed_is_promoted():
    assert verdict(None, {"all": .7, "laptops": .7, "restaurants": .7}) == "promote (nothing deployed)"

def test_missing_scope_is_reported_by_name():
    with pytest.raises(ValueError, match="restaurants"):
        decision_values({"results": {"all": {...}, "laptops": {...}}}, "sentiment")

def test_promote_archives_the_deployed_model_and_copies_the_candidate(tmp_path):
    # models/sentiment has config.json "old"; candidate has config.json "new" + training_log.json
    # -> returns models/previous/sentiment-<stamp>, which holds "old";
    #    models/sentiment/config.json == "new"; models/sentiment/.gitkeep exists;
    #    the candidate folder still holds its files

def test_promote_without_a_deployed_model_archives_nothing(tmp_path):
    # models/overall_sentiment holds only .gitkeep -> returns None, models/previous not created

def test_promote_refuses_an_unfinished_candidate(tmp_path):
    # candidate without training_log.json -> raises FileNotFoundError, deployed folder unchanged

def test_promoting_twice_changes_nothing(tmp_path):
    # second call returns None and creates no second archive
```

- [ ] **Step 2:** Run `pytest tests/test_promote.py -q`. Expected: import error.
- [ ] **Step 3: Implement `promote.py`.**
  - "Deployed" means `models/<name>/config.json` exists.
  - `promote` is a no-op returning `None` when the deployed `training_log.json` has the same bytes as the candidate's (this is what makes a second run harmless).
  - Archive with `shutil.move`, install with `shutil.copytree`, then write an empty `.gitkeep`.
  - `main` reads `models/candidates/eval/current/evaluation_report.json` and `.../candidate/evaluation_report.json`, prints `render_comparison`, and with `--apply` promotes only models whose verdict starts with `promote`, logging each archive path. `stamp` is `datetime.now().strftime("%Y%m%d-%H%M%S")`. Exit code `3` if any verdict is `needs decision`.
  - The overall model's "current" column in the table is labelled `joint backup (reference)`.
- [ ] **Step 4:** Run the test file. Expected: all pass.
- [ ] **Step 5:** Commit `feat(training): compare candidates with deployed models and promote safely`.

### Task 3: Second confusion matrix and result-consistency check

**Files:**
- Modify: `backend/training/evaluate.py` (`render_markdown`, and the figure-writing block in `main`)
- Create: `backend/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `render_markdown(report: dict) -> str` (existing).
- Produces: `docs/figures/overall_confusion_matrix.png`, written next to the existing figure; `results.md` embeds it as `![Overall-sentiment confusion matrix](figures/overall_confusion_matrix.png)` after the overall-sentiment table of the `all` scope.

- [ ] **Step 1: Write the failing tests.** Build a minimal report dict in a fixture (one scope `all`, three training logs, metrics shaped as `classification_metrics` and `span_prf` return them).

```python
def test_results_embed_both_confusion_matrices(report):
    text = render_markdown(report)
    assert "figures/sentiment_confusion_matrix.png" in text
    assert "figures/overall_confusion_matrix.png" in text

def test_results_state_how_the_models_were_selected(report):
    assert "selected over the previously deployed models by comparing test-set scores" in render_markdown(report)

def test_results_include_the_mixed_sentence_row(report):
    assert "| mixed |" in render_markdown(report)

def test_published_results_match_the_published_report():
    # skip if models/evaluation_report.json is missing;
    # else assert f"- Generated: {report['generated_at']}" in docs/results.md
```

- [ ] **Step 2:** Run `pytest tests/test_evaluate.py -q`. Expected: the first two fail; the fourth fails or passes depending on the stale files and must pass after Task 8.
- [ ] **Step 3:** Change `render_markdown` to add the image line and the note, and `main` to call `plot_confusion_matrix` a second time with `results["all"]["overall_sentiment"]["confusion_matrix"]` and the title `"Overall sentiment - test set (weak labels)"`.
- [ ] **Step 4:** Run the test file. Expected: the first three pass.
- [ ] **Step 5:** Commit `feat(evaluate): overall-sentiment confusion matrix and selection note`.

### Task 4: Real-model tests (written now, skipped until Task 7)

**Files:**
- Modify: `backend/tests/conftest.py` (add fixture `real_client`)
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_evaluate.py`

**Interfaces:**
- Produces: fixture `real_client` — like `client`, but with `ABSA_LOAD_MODELS=true` and no dependency override, so the app's `lifespan` loads the deployed models; temporary SQLite database.

- [ ] **Step 1: Write the tests**, each decorated `@pytest.mark.model` and `@requires_models`.

```python
def test_analyze_endpoint_with_the_deployed_models(real_client):
    review = "The screen is gorgeous and the keyboard feels great, but the battery life is terrible."
    body = real_client.post("/api/analyze", json={"review": review}).json()
    assert body["id"] is not None
    assert body["overall_sentiment"] in {"positive", "negative", "neutral"}
    assert body["aspects"], "no aspects extracted"
    for aspect in body["aspects"]:
        assert body["review"][aspect["start"]:aspect["end"]] == aspect["aspect"]
        assert aspect["sentiment"] in {"positive", "negative", "neutral"}
        assert 0.0 <= aspect["confidence"] <= 1.0
    assert real_client.get(f"/api/reviews/{body['id']}").json() == body
    assert real_client.get("/api/health").json()["status"] == "ok"

def test_report_describes_the_deployed_models():   # in test_evaluate.py
    report = json.loads((MODELS_DIR / "evaluation_report.json").read_text())
    for key, folder in (("aspect", ASPECT_MODEL_DIR), ("sentiment", SENTIMENT_MODEL_DIR), ("overall", OVERALL_MODEL_DIR)):
        log = json.loads((folder / "training_log.json").read_text())
        assert report["training"][key]["best_validation_score"] == log["best_validation_score"]
    assert report["domains"] == ["laptops", "restaurants"]
    assert "aspect_sentiment_by_sentence_type" in report["results"]["all"]
```

- [ ] **Step 2:** Run `pytest -q`. Expected: 48 + the new fast tests pass; the model tests are reported as skipped (no overall model yet).
- [ ] **Step 3:** Commit `test: real-model API integration test and report-freshness check`.

### Task 5: Smoke test

**Files:** none in git. Creates and removes `models/candidates/_smoke/`.

- [ ] **Step 1:** `..\.venv\Scripts\python.exe -m training.run_all --smoke`. Expected: exit code 0 in under 10 minutes.
- [ ] **Step 2:** Verify `models/candidates/_smoke/eval/candidate/evaluation_report.json` exists and its `results.all` has the five sections, and that the modification times of `models/aspect_extraction/model.safetensors` and `models/sentiment/model.safetensors` are unchanged (still 2026-10-05 23:48 and 2026-10-06 00:52).
- [ ] **Step 3:** Delete `models/candidates/_smoke/` only. Confirm `python -m training.run_all --status` lists all five steps as pending.
- [ ] **Step 4:** If any step failed: read its log under `_smoke/logs/`, fix the cause, rerun. Do not proceed to Task 6 with a failing smoke test.

### Task 6: Full training run (about 4.5 hours, unattended)

**Files:** none in git. Creates `models/candidates/`.

- [ ] **Step 1:** Tell the user the run is starting and that the laptop must stay plugged in with the lid open.
- [ ] **Step 2:** Launch detached, from `backend/`:

```powershell
Start-Process -FilePath ..\.venv\Scripts\python.exe -ArgumentList '-m','training.run_all' -WorkingDirectory (Get-Location) -WindowStyle Hidden
```

- [ ] **Step 3:** After two minutes run `python -m training.run_all --status`. Expected: `aspect` running, with a step-progress line from its log.
- [ ] **Step 4:** Check status at each expected step boundary (about 60, 180, 235, 250 and 265 minutes). If the process has died (lock present, no python process), remove the lock and relaunch: completed models are skipped.
- [ ] **Step 5:** Done when `--status` shows all five steps `done`. Record each model's `training_minutes` and `best_validation_score` from its `training_log.json` for the hand-over message.

### Task 7: Compare and promote

**Files:** `models/` only (not in git).

- [ ] **Step 1:** `python -m training.promote`. Show the user the full comparison output.
- [ ] **Step 2:** If any verdict is `needs decision`: stop and ask the user which model to keep for that slot. Do not pass `--apply` for it.
- [ ] **Step 3:** `python -m training.promote --apply`. Expected: one archive line per previously deployed model (`aspect_extraction`, `sentiment`), none for `overall_sentiment`.
- [ ] **Step 4:** Verify: the three `models/<name>/` folders each contain `config.json` and `training_log.json`; `models/previous/` holds the two archived folders with their original weights; `models/sentiment_joint_backup/` and `models/train_sentiment_aspect.log` are unchanged.

### Task 8: Final evaluation and full verification

**Files:**
- Regenerated: `models/evaluation_report.json`, `docs/results.md`, `docs/figures/sentiment_confusion_matrix.png`, `docs/figures/overall_confusion_matrix.png`

- [ ] **Step 1:** `python -m training.evaluate`. Expected: the summary prints both domains and `docs/results.md` gains sections "Domain: laptops" and "Domain: restaurants".
- [ ] **Step 2:** `python -m pytest -q`. Expected: every test passes and **none is skipped**. If `test_end_to_end_with_trained_models` or `test_model_separates_aspects_of_one_sentence` fails, report the model's actual output to the user; do not edit the assertion.
- [ ] **Step 3:** Live check. Start `uvicorn app.main:app --port 8000`, then:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/analyze -ContentType "application/json" -Body '{"review": "The pasta was delicious but the service was slow.", "save": false}' | ConvertTo-Json -Depth 5
(Invoke-RestMethod http://localhost:8000/api/model-info).report.domains
```

Expected: `status` is `ok`; the restaurant review returns at least one aspect; domains are `laptops restaurants`. Stop the server.
- [ ] **Step 4:** Commit `docs(results): regenerate evaluation from the two-domain models` (results, figures; the report JSON is committed too, since `.gitignore` excludes only `models/*/*`).

### Task 9: Documentation

**Files:**
- Modify: `README.md` (status table; "Train the models" commands; repository layout)
- Modify: `backend/training/README.md` (add `run_all`, `promote`, the resume rule, `--status`)
- Modify: `docs/methodology.md` (section 4.3 pointer to the mixed-sentence row; section 7)
- Modify: `docs/API.md` (`/model-info` example: both domains, `overall` under `training`, `aspect_sentiment_by_sentence_type`)
- Modify: `CONTRIBUTING.md` (tick "Retrain on ... both domains"; step 3 of "Get it running")
- Modify: `docs/PROJECT_CHECKLIST.md` (mark sub-project 1 rows completed)

- [ ] **Step 1:** In `README.md` replace the three training commands with `python -m training.run_all` followed by `python -m training.promote --apply` and `python -m training.evaluate`, keep the per-script commands as the manual alternative, and replace "about 2.5 hours" with the sum of the three `training_minutes` values measured in Task 6.
- [ ] **Step 2:** Make the other edits listed above. Every statement about model quality must point to `docs/results.md` rather than quote a number.
- [ ] **Step 3:** `git grep -n "laptops" -- "*.md"` and check that no remaining sentence says the shipped models are laptops-only.
- [ ] **Step 4:** `python -m pytest -q` once more, then commit `docs: describe the two-domain training and promotion workflow`.
- [ ] **Step 5:** Ask the user whether `models/candidates/`, `models/previous/`, `models/sentiment_joint_backup/` and `models/train_sentiment_aspect.log` may be removed. Remove nothing without an answer. Note that sub-project 3 uses `models/candidates/eval/current/` for the cross-domain analysis.
