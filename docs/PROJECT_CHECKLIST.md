# Full-project checklist

State of every module on 2026-10-09, what it depends on, and how it is tested.
Status is one of **Completed**, **Partial** or **Pending**. "SP" is the
sub-project that finishes the row; each sub-project gets its own spec and plan
under `docs/superpowers/`.

| SP | Scope | Order |
|---|---|---|
| 1 | Models and evaluation | first: every later part shows or reports these numbers |
| 2 | Frontend application | second; can be designed while SP1 trains |
| 3 | NLP analysis: baseline, error analysis, notebooks, transfer | third; needs SP1's models |
| 4 | Delivery: Docker, report, slides, repository | last; needs everything above |

## A. Data

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| Dataset download and validation (`training/prepare_dataset.py`) | Completed | network on first run | `tests/test_dataset.py` | - |
| Train / validation / test split, leakage check | Completed | above | `tests/test_dataset.py` | - |
| Dataset statistics (`data/processed/dataset_stats.json`) | Completed | above | generated; quoted in `docs/methodology.md` | - |

## B. NLP core

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| Preprocessing: cleaning, sentences, tokens, BIO, context | Completed | NLTK | `tests/test_preprocessing.py` | - |
| Aspect-extraction wrapper and tag-to-span logic | Completed | preprocessing | `tests/test_aspect.py` | - |
| Sentiment wrapper, aspect and overall classification | Completed | preprocessing | `tests/test_sentiment.py` | - |
| End-to-end pipeline (`nlp/pipeline.py`) | Completed | the three above | `tests/test_pipeline.py` (stub models) | - |

## C. Models

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| Training scripts (`train_aspect`, `train_sentiment`) | Completed | A | smoke run with `--limit 32` | - |
| Aspect-extraction model | Partial: trained on laptops only | training scripts | span F1 on both test domains | 1 |
| Aspect-sentiment model | Partial: weights from an interrupted run, no training log, laptops only | training scripts | macro-F1, mixed-sentence accuracy on both domains | 1 |
| Overall-sentiment model | Pending: folder is empty, so the app cannot analyse | training scripts | macro-F1 against weak labels | 1 |
| Resumable training chain (`training/run_all.py`) | Pending | training scripts | `tests/test_run_all.py` | 1 |
| Comparison and promotion (`training/promote.py`) | Pending | run_all output | `tests/test_promote.py` | 1 |

## D. Evaluation

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| Metrics (`training/metrics.py`) | Completed | - | `tests/test_dataset.py` | - |
| Evaluation script (`training/evaluate.py`) | Partial: no overall-sentiment figure, no unit tests | C | `tests/test_evaluate.py` (new) | 1 |
| `docs/results.md`, `models/evaluation_report.json` | Partial: describe the old joint model, laptops only, no mixed-sentence row | deployed models | report-freshness test (new) | 1 |
| Confusion-matrix figures | Partial: one of two | evaluate | file exists and is embedded in `results.md` | 1 |
| Real-model tests (7 existing) | Partial: all skipped today because a model is missing | deployed models | `pytest` with zero skips | 1 |

## E. Backend API

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| `POST /api/analyze` | Completed in code; answers 503 today | C | `tests/test_api.py` (stubs); real-model integration test (new) | 1 |
| `POST /api/analyze/batch` | Completed | C | `tests/test_api.py` | - |
| History: list, get, delete | Completed | database | `tests/test_api.py`, `tests/test_database.py` | - |
| `GET /api/statistics` | Completed | database | `tests/test_api.py` | - |
| `GET /api/health`, `GET /api/model-info` | Completed; model-info serves stale numbers today | D | `tests/test_api.py`; freshness test (new) | 1 |
| Validation and error shape (422, 404, 503, 500) | Completed | - | `tests/test_api.py` | - |
| SQLite storage (SQLAlchemy) | Completed | - | `tests/test_database.py` | - |
| Configuration, CORS, logging | Completed | - | `tests/test_api.py` | - |
| CSV batch handling for large files | Pending: the endpoint takes at most 50 reviews and is all-or-nothing | batch endpoint | decided in SP2's spec: chunk in the browser, or add an upload endpoint | 2 |

## F. Frontend

The scaffold exists: routing, typed API client, `useApi`, connection indicator,
and four pages that print raw JSON. `npm run build` passes. Everything a user
sees is still to build.

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| API client and types (`services/api.ts`, `types/api.ts`) | Completed; `ModelInfoResponse` is untyped | E | type-check; client tests (new) | 2 |
| Review-input workflow: text box, example reviews, character count against the 5000 limit, blank-input guard, save toggle, submit and loading state | Partial: plain textarea and button | `/analyze` | component tests | 2 |
| Overall-sentiment result: label, confidence, "traditional view" framing | Pending | `/analyze` | component tests | 2 |
| Aspect-level results: table with aspect, sentiment, confidence, context | Pending | `/analyze` | component tests | 2 |
| Aspects highlighted inside the review text using `start`/`end` | Pending | `/analyze` | component test with overlapping-free spans | 2 |
| Per-review sentiment chart | Pending | Recharts | render test | 2 |
| Traditional versus aspect-based comparison view | Pending | `/analyze` | component test | 2 |
| Error handling: backend unreachable, models not loaded (503), invalid input (422), server error (500), request in flight | Partial: one red text line | `ApiError` | tests with a mocked client for each case | 2 |
| Empty states: no aspects found, no history, no statistics | Pending | - | component tests | 2 |
| Home page: explanation, worked example | Partial: title and one paragraph | - | render test | 2 |
| History page: table, pagination, sentiment filter, delete with confirmation, detail view | Pending | `/reviews` | component tests | 2 |
| Dashboard: sentiment distribution, aspect frequency, sentiment per aspect | Pending | `/statistics` | render tests | 2 |
| Model-performance card | Pending | `/model-info`, SP1's report | component test against a sample report | 2 |
| Batch page: CSV upload, progress, result table, CSV export | Pending | `/analyze/batch` | parser unit tests, component test | 2 |
| Responsive layout, keyboard and screen-reader basics | Pending | all pages | manual check at phone and desktop width | 2 |
| Frontend test setup (Vitest, React Testing Library) | Pending | - | `npm test` | 2 |
| Remove `JsonPreview` and the `TODO(frontend team)` comments | Pending | all pages | `git grep` finds none | 2 |

## G. NLP analysis

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| Non-BERT baseline (noun phrases + sentiment lexicon), scored by the same evaluation | Pending | D | unit tests; row in `results.md` | 3 |
| Error analysis: missed aspects, confused sentiments, neutral class, mixed sentences | Pending | SP1 models | notebook runs top to bottom | 3 |
| Cross-domain transfer: laptops-only models on restaurant reviews | Pending; SP1 produces the report it needs | `models/candidates/eval/current/` | numbers come from that report | 3 |
| Reviews from another product category | Pending; no labelled data in the repo, so qualitative unless you supply a dataset | SP1 models | documented examples | 3 |
| Notebooks `01_data_exploration`, `02_preprocessing`, `03_model_evaluation` | Pending | A, D; adds Jupyter as a dev dependency | each executes without error | 3 |

## H. Documentation

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| `README.md` | Partial: training section and status table describe the old models | SP1 | commands in it are the ones run | 1, then 4 |
| `docs/architecture.md` | Completed | - | review | - |
| `docs/methodology.md` | Partial: refers to a results row that does not exist yet | SP1 | review against `results.md` | 1 |
| `docs/API.md` | Partial: `model-info` example is the old layout | SP1 | review against the live response | 1 |
| `docs/results.md` | Partial (see D) | SP1 | generated | 1 |
| `CONTRIBUTING.md`, `frontend/README.md` | Partial: open-task lists will be out of date | SP1 to SP3 | review | each SP |
| Screenshots of the finished interface | Pending | SP2 | present in README and report | 4 |

## I. Delivery

| Module | Status | Depends on | Tested by | SP |
|---|---|---|---|---|
| Git history | Pending: the repository has zero commits and no remote | your approval | `git log` | 1 (first commit), 4 |
| Sharing the trained models (3 x 420 MB, not in git) | Pending | SP1 | a teammate can run the app from a fresh clone | 4 |
| `Dockerfile`s and `docker-compose.yml` | Pending | SP1, SP2 | `docker compose up` serves the app | 4 |
| Continuous integration (fast tests, frontend build) | Pending | a remote repository | workflow passes | 4 |
| Project report | Pending | SP1 to SP3 | every number traces to `results.md` | 4 |
| Presentation slides | Pending | report | review | 4 |
| Demo data and a demo script | Pending | SP2 | scripted run-through works | 4 |

## Open questions

These do not block sub-project 1.

1. The docs mention "the project plan" (suggested components, notebook names),
   but no such document is in the repository. If a synopsis or marking scheme
   exists, add it so the checklist can be checked against it.
2. Report and slides: required format, template, length and deadline.
3. Is there a labelled review dataset for another product category, or is a
   qualitative test enough?
4. How will teammates receive the models: shared drive, or a hosted model
   repository?
