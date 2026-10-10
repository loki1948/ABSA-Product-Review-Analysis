# Full-project checklist

State on 2026-10-10. **The project is not declared 100% complete**: the
assignment's own requirements could not be checked (section 1), Docker has not
been run, and the items in section 4 are open.

How to read the tables:

- **Implemented**: the code or document exists on `feature/models-evaluation`.
- **Tested**: how it was verified, with the evidence.
- **Reviewed**: "yes" means an independent reviewer (a separate reviewer with
  no part in writing the code) examined it on 2026-10-10. "fix" means it was
  changed afterwards in response to that review; those changes are covered by
  new tests but have **not** been reviewed a second time.

Test totals at the last run: backend `pytest` 139 passed, 0 skipped, 0 failed
(including 10 tests on the real models); frontend `npm test` 103 passed;
`npm run build` passes.

## 1. Assignment requirements

No synopsis, assignment brief or marking scheme exists in the repository (no
PDF, Word or PowerPoint file anywhere outside `docs/submission`, and no mention
of one in any tracked file). The only statements of intent are the project
title and the scaffold's own notes in the first commit, so the comparison below
is against those. **Mandatory assignment requirements remain unverified until
the brief is provided.**

| Requirement found in the repository | Source | Implemented | Tested |
|---|---|---|---|
| Aspect-based sentiment analysis of product reviews with NLP | Project title | Yes | Sections 2.2 to 2.4 |
| Both stages are learnt models, no hard-coded aspect list, no external sentiment API | First commit, `CONTRIBUTING.md` | Yes | `test_model_finds_an_aspect_it_was_never_given_a_list_of`; the baseline lives outside `app/` |
| Components `ReviewInput`, `SentimentCard`, `AspectTable`, `SentimentChart` | First commit, `frontend/README.md` | Yes (`SentimentChart` is `AspectSentimentChart`) | Component tests |
| Pages Home, Analyzer, History, Dashboard | First commit | Yes, plus Batch | Page tests, browser run |
| Notebooks `01_data_exploration`, `02_preprocessing`, `03_model_evaluation` | First commit, `CONTRIBUTING.md` | Yes | Each executed without error |
| Retrain on both domains; non-BERT baseline; error analysis; another product category | First commit, open-work list | Yes; the other category is an illustration only | Section 2.6 |
| CSV upload using the batch endpoint; `docker-compose.yml`; report and slides | First commit, open-work list | Yes | Docker **not run** |
| Stated technology: PyTorch, Transformers, scikit-learn, NLTK, pandas, FastAPI, SQLAlchemy, React, TypeScript, Tailwind, Recharts | First commit, `README.md` | All in use | Suites above |

## 2. Modules

### 2.1 Data and preprocessing

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Dataset download, validation, split | Yes | `test_dataset.py`; 0 sentences shared between splits (notebook 01 and reviewer's own check) | yes |
| Preprocessing, BIO tags, context | Yes | `test_preprocessing.py`; notebook 02 | yes |

### 2.2 Models and training

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Three BERT models on both domains | Yes | Test set: aspect F1 0.8462; aspect sentiment accuracy 0.8151, macro-F1 0.7456; end-to-end F1 0.6977; overall macro-F1 0.7202 | yes: published numbers match the report files |
| Training chain `run_all` | Yes | 19 tests; one full run completed | fix: stale evaluations are detected, a fresh clone can finish, the lock names its owner, the display is kept awake |
| Promotion `promote` | Yes | 16 tests; all three candidates met the rule on both domains | fix: never deletes a folder that holds more than the placeholder; installs by rename; compares only with models the report describes |
| `--limit` trial runs | Yes | `test_limit_cannot_overwrite_published_or_deployed_outputs` | fix: refused on real output paths |

### 2.3 Evaluation

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| `results.md`, `evaluation_report.json`, two confusion matrices | Yes | Generated from the deployed models; `test_report_describes_the_deployed_models` | yes |
| `/api/model-info` serves that report | Yes | Browser run showed the three test sets | yes |

### 2.4 Backend API

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Analyze, batch, history, statistics, health, model info | Yes | `test_api.py` with stubs and with the real models | yes: no SQL injection, sessions closed, contract matches the frontend |

### 2.5 Frontend

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Analyzer: input workflow, overall and aspect results, highlighting | Yes | Component and page tests; browser: laptop and restaurant reviews, no-aspect case, keyboard only (Ctrl+Enter, Tab, Space, Enter) | yes |
| Error states: backend unreachable, models not loaded, invalid input, server error | Yes | Tests; browser on every page | yes |
| History: paging, filter, full analysis, delete | Yes | `History.test.tsx`; browser | yes |
| Dashboard and model performance | Yes | `Dashboard.test.tsx`; browser | yes |
| Batch: paste or CSV, chunks, progress, cancel, export | Yes | 12 tests; browser: real file upload of `demo_reviews.csv` (12 reviews), real download of `absa-results.csv` (28 data rows) | fix: formula characters neutralised in the export; pasted reviews kept whole; continues instead of resending; stops when the page is left |
| Phone width (390 px) | Yes | Scripted browser check on all five pages: no sideways scrolling, nothing cut off. Found and fixed an overflow on Home, Analyzer and History | not reviewed (reviewer had no browser) |
| Screenshots | Yes | `docs/screenshots` (11 images) from `frontend/scripts/browser-checks.mjs` | not applicable |

### 2.6 NLP analysis

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Rule-and-lexicon baseline | Yes | 14 tests; `docs/baseline.md`: aspect F1 0.3765 against 0.8462 | yes: same data and metric functions, supports match exactly |
| Error analysis | Yes | 11 tests; `docs/error_analysis.md` | yes |
| Transfer to an unseen domain | Yes | `docs/transfer.md`: laptops-only aspect extractor on restaurants, F1 0.3704 against 0.8715 | fix: the comparison is now limited to aspect extraction. The earlier sentiment model has no training record, so no claim is made from it |
| Other product categories | Illustration only | Twelve hand-written reviews; no annotated data, no accuracy figure | yes |
| Notebooks | Yes | All three execute without error | partly (contents not judged) |

### 2.7 Documentation and submission files

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| README, CONTRIBUTING, architecture, methodology, API | Yes | Commands are the ones that were run | fix: methodology no longer quotes two figures that no report file contains |
| Report source `docs/report.md`, slides source `docs/slides.md` | Yes | Generated by `training/report.py` (6 tests) from the report files | yes: every 4-decimal figure traced to a report file |
| `docs/submission/ABSA_Project_Report.docx` and `.pdf` | Yes | Built by `training/export.py` (7 tests) and Word; 29 pages; includes appendices A to D and four screenshots | Layout not proofread by a person |
| `docs/submission/ABSA_Presentation.pptx` and `.pdf` | Yes | 18 slides, four of them screenshots; two slides inspected as images | Plain default design; not proofread by a person |
| Demo script, model sharing, model recovery | Yes | Demo steps match the browser run | not reviewed |

### 2.8 Delivery

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Git branch | Yes | Clean tree; no weights, datasets or env files tracked | yes |
| CI workflow `.github/workflows/ci.yml` | Yes | **Not run**: the repository has no remote | no |
| Model archive | Yes | `absa-models.zip` (1.14 GB) with SHA-256 file, made by `scripts/package_models.ps1`; weights sizes match the deployed ones | no |
| Docker | Written | **Never run**: Docker is not installed here | static reading only |

## 3. Independent review: what remains

Fixed: all 11 "Important" findings (sections above, marked "fix").
Not fixed, recorded as minor:

- Tracked report files contain the local path `C:\Users\Admin\...` in the
  training logs' `output_dir`, and `/api/model-info` serves it.
- No request-body size limit when running plain uvicorn.
- `clean_text` removes text between `<` and `>` ("battery <3 hours, screen >13
  inch"); a review consisting only of a tag is stored as empty text.
- A batch that fails on saving can leave earlier reviews saved.
- `requirements.txt` gives minimum versions only; there is no lock file.
- Docker: the health check allows about 135 seconds for loading the models;
  the backend container runs as root.
- `ConfirmDialog` has no focus trap; an out-of-range `?page=` in History shows
  the empty message; the Analyzer reads the health status only once.
- The baseline finds an aspect's clause by text search, a small handicap for
  the baseline.
- The report's concluding sentences are fixed text and would not follow
  different numbers after a retrain.

## 4. Pending

1. **Provide the assignment brief or marking scheme**, so section 1 can be
   checked against the real requirements.
2. **Run Docker** on a machine that has it: `docker compose up --build`, open
   http://localhost:8080, analyse one review, check History and Dashboard.
3. **Push to a remote** so CI runs once; merge into `main` after that.
4. **Copy `absa-models.zip` and its `.sha256` off this machine**; until then
   every copy of the models is on one disk.
5. A person should proofread the DOCX and the slides and restyle the slides if
   a template is required.
6. Decide on removing the 2.44 GB of model backups
   ([model_recovery.md](model_recovery.md) lists what each removal costs).
7. The fixes made after the review have not been reviewed a second time.

## 5. Known limitations of the result

- Neutral is the weakest sentiment class, and sentences that mix sentiments
  are the hardest case (accuracy 0.6616 against 0.8507 for uniform sentences).
- One training run, one seed; the deployed models were chosen by comparing
  test scores, which makes the reported scores slightly optimistic.
- On hand-written reviews of other product categories the pipeline makes
  visible mistakes, for example "room" marked negative in "The room was
  spotless".
