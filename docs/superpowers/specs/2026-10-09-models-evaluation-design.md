# Sub-project 1: Models and evaluation — design

Date: 2026-10-09. Status: awaiting review. Part 1 of 4; the other parts and
their order are in [../../PROJECT_CHECKLIST.md](../../PROJECT_CHECKLIST.md).

## 1. Goal

Three finished BERT models trained on both SemEval-2014 domains (laptops and
restaurants), an application that can analyse a review end to end, and
documentation whose every number comes from exactly the models that are
deployed.

Success means all of the following are true:

1. `models/aspect_extraction`, `models/sentiment` and `models/overall_sentiment`
   each hold a model with a `training_log.json`.
2. `docs/results.md`, `models/evaluation_report.json` and the confusion-matrix
   figures were generated from those three models, on both test domains.
3. `pytest` passes with no skipped tests, including a new test that posts a
   review to `/api/analyze` through the real models.
4. The models that were deployed before this work still exist on disk.

## 2. What the inspection found (2026-10-09)

| Finding | Evidence | Consequence |
|---|---|---|
| The overall-sentiment model does not exist | `models/overall_sentiment/` holds only `.gitkeep` | `ABSAPipeline.from_pretrained` raises, `/api/analyze` answers 503, the 7 model tests are skipped |
| The deployed aspect-sentiment model has unknown provenance | `models/sentiment/` has weights saved 2026-10-06 00:52 but no `training_log.json`; the log is written only when a run finishes | The run that produced it was interrupted after saving one epoch's checkpoint. Its epoch, domains and validation score are unrecorded |
| A later retrain also died | `models/train_sentiment_aspect.log` stops at step 175 of 1332 (2026-10-08) | No checkpoint was saved by that run |
| The published results describe a model that is not deployed | `models/evaluation_report.json` and `models/sentiment_joint_backup/evaluation_report_joint.json` carry the same timestamp; the report has no `aspect_sentiment_by_sentence_type` section and no `overall` training entry | `docs/results.md` and `GET /api/model-info` report the old joint model. `docs/methodology.md` refers to a mixed-sentence row that `results.md` does not contain |
| All shipped models are laptops-only | `training_log.json` of the aspect model; "domains: laptops" in `results.md` | Restaurant reviews are out of domain today |
| The fast test suite is healthy | 48 passed, 7 deselected | The code path is sound; the gap is models and reporting |

## 3. Decisions

- **Train all three models from scratch on both domains, on this CPU.** Chosen
  by the user over a Colab run.
- **Hyperparameters are the scripts' defaults**, unchanged: aspect extraction
  3 epochs at 3e-5, both sentiment models 4 epochs at 2e-5, batch size 16,
  max length 128, seed 42, `bert-base-uncased`. No hyperparameter search: each
  extra run costs one to two hours here.
- **Candidates first.** Training writes to `models/candidates/<name>/`. The
  three deployed folders are not touched until promotion.
- **Sequential runs.** The machine has 8 logical cores and PyTorch already uses
  them; parallel runs would only slow each other down.
- **Promotion is a separate, explicit step**, run after the comparison has been
  read. It is not part of the unattended chain.
- **Nothing is deleted.** Promotion moves the previous model into
  `models/previous/`. `models/sentiment_joint_backup/`,
  `models/train_sentiment_aspect.log` and `models/candidates/` stay until the
  user approves their removal. The one exception is the smoke-test output
  (section 4.1), which this work creates and removes itself.

## 4. Process

### 4.1 Smoke test

Before any long run, every step of the chain runs once on 32 sentences for one
epoch, writing to `models/candidates/_smoke/`. It must finish without error and
leave three loadable models and one evaluation report. Expected duration: under
10 minutes. `_smoke/` is deleted when the smoke test passes, because a leftover
`training_log.json` there must never be mistaken for a finished model.

### 4.2 Training chain

One runner, `python -m training.run_all`, executes these steps in order:

| # | Step | Command it runs | Output | Estimate |
|---|---|---|---|---|
| 1 | Aspect extraction | `training.train_aspect --output-dir models/candidates/aspect_extraction` | 1023 steps | 60 min |
| 2 | Aspect sentiment | `training.train_sentiment --task aspect --output-dir models/candidates/sentiment` | 1332 steps | 120 min |
| 3 | Overall sentiment | `training.train_sentiment --task overall --output-dir models/candidates/overall_sentiment` | about 780 steps | 55 min |
| 4 | Evaluate candidates | `training.evaluate` on laptops and restaurants | `models/candidates/eval/candidate/` | 15 min |
| 5 | Evaluate deployed models | `training.evaluate` on laptops and restaurants | `models/candidates/eval/current/` | 15 min |

Estimates use the step times in the existing logs (3.4 to 5.3 s per step).
Total: about 4.5 hours.

Step 5 needs an overall model to run. None is deployed, so it reads
`models/sentiment_joint_backup` in that slot. That folder is only read.

Runner behaviour:

- **Resumable per step.** A training step is complete when its output folder
  contains `training_log.json`; an evaluation step when its
  `evaluation_report.json` exists. Complete steps are skipped. An incomplete
  step restarts from the beginning: the training loop has no mid-run resume,
  and adding one is out of scope. A folder holding weights but no
  `training_log.json` counts as incomplete.
- **Stops at the first failure** with a non-zero exit code and the step's name.
- **Logs** each step to `models/candidates/logs/<step>.log` and its own
  progress to `models/candidates/logs/run_all.log`.
- **Keeps the machine awake** while it runs (Windows
  `SetThreadExecutionState`; a no-op elsewhere). Closing the lid still
  suspends the laptop.
- **`--status`** prints which steps are done, running or pending and the last
  line of the active log.
- It is launched as a detached process so that closing the terminal or the
  assistant session does not kill it.

### 4.3 Comparison and promotion

`python -m training.promote` reads the two reports from steps 4 and 5 and
prints one table per model:

| Model | Decision metric | Also shown |
|---|---|---|
| Aspect extraction | span F1 | precision, recall, end-to-end F1 |
| Aspect sentiment | macro-F1 | accuracy, accuracy on mixed sentences |
| Overall sentiment | macro-F1 | accuracy |

Each table has the scopes `all`, `laptops` and `restaurants`, with deployed
value, candidate value and difference.

Verdict per model:

- `promote`: the candidate's decision metric on `all` is higher than the
  deployed model's, and on neither single domain is it lower by more than
  0.01.
- `needs decision`: anything else. Work stops and the user decides.
- The overall-sentiment candidate has no deployed counterpart. Its verdict is
  `promote (nothing deployed)`; the joint backup's numbers are shown for
  reference only.

`python -m training.promote --apply` then, for every model whose verdict is
`promote`:

1. moves `models/<name>/` to `models/previous/<name>-<YYYYMMDD-HHMMSS>/` if it
   contains a model;
2. copies `models/candidates/<name>/` to `models/<name>/`.

It refuses to run if a candidate lacks `training_log.json`, and it never
promotes a `needs decision` model.

A known cost of this rule: choosing between two models by their test scores is
a mild use of the test set for selection. With two candidates per model and a
0.01 tolerance the effect is small; `results.md` will say that the comparison
was made.

The step-5 report has a second use. The deployed aspect and sentiment models
were trained on laptops only, so their restaurant scores measure cross-domain
transfer. Sub-project 3 uses that report, which is one reason
`models/previous/` and `models/candidates/eval/` are kept.

### 4.4 Final evaluation and consistency

After promotion, `python -m training.evaluate` runs with its default paths and
rewrites `models/evaluation_report.json`, `docs/results.md` and the figures.

Two changes to `training/evaluate.py`:

- a second figure, `docs/figures/overall_confusion_matrix.png`, embedded in
  `results.md` beside the overall-sentiment table;
- one more line under "Notes for interpreting these numbers" stating that the
  deployed models were selected over the previous ones by test-set comparison.

New automated checks:

| Test | Needs models | Asserts |
|---|---|---|
| `/api/analyze` through the real models | yes | 200; every aspect satisfies `review[start:end] == aspect`; sentiments are valid labels; the saved review is returned by `GET /api/reviews/{id}`; `/api/health` reports `ok` |
| The report describes the deployed models | yes | for each of the three models, `best_validation_score` in `evaluation_report.json` equals the one in `models/<name>/training_log.json`; the report covers laptops and restaurants and contains the mixed-sentence section |
| `results.md` matches the report | no | the "Generated:" line equals the report's `generated_at`; skipped when no report exists |

The second test is the one that would have caught the stale report found in
section 2.

### 4.5 Documentation

Updated to describe what was actually run, with no hand-typed metrics:

- `README.md`: status table, the training commands, repository layout
  (`models/candidates`, `models/previous`).
- `backend/training/README.md`: `run_all`, `promote`, the resume rule.
- `docs/methodology.md`: the sentence in 4.3 that points at the mixed-sentence
  row, and the limitations list where the retrain changes it.
- `docs/API.md`: the `model-info` example (two domains, new sections).
- `CONTRIBUTING.md`: tick the retrain item; record remaining accuracy work.

## 5. Out of scope

- Hyperparameter search, other base models, multiple seeds.
- Fixing the neutral class or mixed-sentence accuracy. More data should help;
  sub-project 3 measures what remains.
- Any frontend change (sub-project 2), the non-BERT baseline, notebooks and
  error analysis (sub-project 3), Docker, report and slides (sub-project 4).

## 6. Risks

| Risk | Handling |
|---|---|
| The laptop sleeps or the run is killed | Sleep is blocked; the run is detached; a restart resumes at the unfinished model |
| A candidate is worse on laptops than the deployed model | `needs decision` verdict; the deployed model stays in place |
| The real-model test in `test_pipeline.py` fails on the new models (it expects `screen` positive and `battery life` negative) | Reported as a finding with the model's actual output; the test is not weakened to pass |
| Disk space | Candidates plus archives are about 3 GB; 153 GB is free |
| No network | `bert-base-uncased` is already in the local Hugging Face cache |
