# Full-project checklist

State on 2026-10-20. **The project is not declared 100% complete**: the
assignment's own requirements could not be checked (section 1), Docker has not
been run, and the items in section 4 are open.

How to read the tables:

- **Implemented**: the code or document exists on `feature/models-evaluation`.
- **Tested**: how it was verified, with the evidence.
- **Reviewed**: "yes" means an independent reviewer (a separate reviewer with
  no part in writing the code) examined it on 2026-10-10. "fix" means it was
  changed in response to a review. There were three reviews: the first of
  the whole branch (2026-10-10), the second of the fixes for the first
  (2026-10-10), the third of the fixes for the second (2026-10-20). The
  fixes for the third review are covered by new tests, each checked to fail
  on the code before the fix (section 3).

Test totals at the last run (2026-10-20): backend `pytest -m "not model"` 149
passed, 0 failed; the 10 tests on the real models were last run on 2026-10-10
(all passed) and were not rerun, since no model or API code changed and this
machine is short of memory. Frontend `npm test` 114 passed; `npm run build`
passes.

Each open item is waiting for exactly one of four things, named in section 4:
a **remote repository**, a **Docker environment**, an **external backup**, or
the **assignment brief**. Everything else in this file is verified on this
machine.

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
| Training chain `run_all` | Yes | 20 tests; one full run completed | fix: stale evaluations are detected, a fresh clone can finish, the lock names its owner, the display is kept awake |
| Promotion `promote` | Yes | 25 tests; all three candidates met the rule on both domains | fix: never deletes a folder that holds more than the placeholder; installs by rename; compares only with models the report describes; reports repairs; a model in use no longer stops the other slots (exit code 4) |
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
| Batch: paste or CSV, chunks, progress, cancel, export | Yes | 17 page tests and 30 CSV tests; browser: real file upload of `demo_reviews.csv` (12 reviews), real download of `absa-results.csv` (28 data rows). The "Read the text as" switch added after the third review: page tests, and a browser check on 2026-10-21 at 1366 px and 390 px (upload sets the mode, editing keeps it, mouse, arrow keys and tap switch it, locked during a run, 44 px tap targets, no sideways scrolling) | fix (all three reviews): formula characters neutralised in the export; a `.csv` upload is read as CSV, a `.txt` upload and typed text one review per line; editing an upload keeps its mode, shown and changeable with a visible switch; continues instead of resending; stops when the page is left |
| Phone width (390 px) | Yes | Scripted browser check on all five pages: no sideways scrolling, nothing cut off. Found and fixed an overflow on Home, Analyzer and History | not reviewed (reviewer had no browser) |
| Screenshots | Yes | `docs/screenshots` (11 images) from `frontend/scripts/browser-checks.mjs` | not applicable |

### 2.6 NLP analysis

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Rule-and-lexicon baseline | Yes | 14 tests; `docs/baseline.md`: aspect F1 0.3765 against 0.8462 | yes: same data and metric functions, supports match exactly |
| Error analysis | Yes | 12 tests; `docs/error_analysis.md` | yes |
| Transfer to an unseen domain | Yes | `docs/transfer.md`: laptops-only aspect extractor on restaurants, F1 0.3704 against 0.8715 | fix: the comparison is now limited to aspect extraction. The earlier sentiment model has no training record, so no claim is made from it |
| Other product categories | Illustration only | Twelve hand-written reviews; no annotated data, no accuracy figure | yes |
| Notebooks | Yes | All three execute without error | partly (contents not judged) |

### 2.7 Documentation and submission files

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| README, CONTRIBUTING, architecture, methodology, API | Yes | Commands are the ones that were run | fix: methodology no longer quotes two figures that no report file contains |
| Report source `docs/report.md`, slides source `docs/slides.md` | Yes | Generated by `training/report.py` (6 tests) from the report files | yes: every 4-decimal figure traced to a report file |
| `docs/submission/ABSA_Project_Report.docx` and `.pdf` | Yes | Built by `training/export.py` (10 tests) and Word; 27 pages; appendices A to D and four screenshots. Proofread as page images: every page of the first build, then 12 pages again after the layout fixes; text scanned for placeholders, missing images and leftover Markdown (none) | Names, roll numbers and supervisor are not in the repository and so not on the title page |
| `docs/submission/ABSA_Presentation.pptx` and `.pdf` | Yes | 18 slides, four of them screenshots placed after the System slide. Every slide inspected as an image in the first build, six again after the layout fixes; numbers match the report | Plain default design; no names on the title slide |
| Demo script, model sharing, model recovery | Yes | Demo steps match the browser run | not reviewed |

### 2.8 Delivery

| Module | Implemented | Tested | Reviewed |
|---|---|---|---|
| Git branch | Yes | Clean tree; no weights, datasets or env files tracked | yes |
| CI workflow `.github/workflows/ci.yml` | Yes | **Not run: awaiting a remote.** The second reviewer ran the fast backend suite on a clean export of the repository (no models, no data) and it passed, which is what the workflow does; an actual run on GitHub has not happened | static reading |
| Model archives | Yes | `absa-models.zip` (deployed models, 18 files) and `absa-history.zip` (earlier models, run records, old log, 35 files), each with a SHA-256 file. Every entry of both was compared by hash with the file on disk: all identical. **Awaiting an external backup**: both archives are still on this machine's only disk | script reviewed statically |
| Docker | Written | **Untested: awaiting a Docker environment.** Never run; Docker is not installed here | static reading only |

## 3. Independent reviews

**First review** (whole branch): no critical findings, 11 important ones. All
11 were fixed with tests.

**Second review** (of those fixes): 5 of the 11 fully closed, 6 partly closed,
and 7 new important findings, all in the fixes themselves. All 7 are fixed with
tests:

| Finding | Fix | Test |
|---|---|---|
| `promote --apply` installed candidates without comparison when the installed model had not been evaluated | A slot with an unevaluated installed model gets "needs decision" | `test_installed_model_that_was_never_evaluated_is_not_replaced_unseen`, `test_stale_current_report_does_not_count_as_a_comparison` |
| Uploaded CSV files without a `review` column were read as whole lines | Files are always read as CSV with the first-column fallback | `csv.review2.test.ts` |
| A pasted first line containing "Text" or "Review" was taken for a header | Typed text is always one review per line | `csv.review2.test.ts` |
| A locked file could leave the installed model half-moved | The old model is archived by a single rename; on failure it stays intact | `test_model_in_use_is_left_intact` |
| `--limit` could still overwrite the published figures | Refused whenever the output folder is `docs/` | `test_limit_cannot_overwrite_the_published_figures` |
| The recovery guide described a repair that did not always happen | "already installed" models are always checked and re-copied if incomplete; guide corrected | `test_candidate_that_is_already_installed_says_so_and_can_be_repaired` |
| A killed parent's lock could be taken over while its training child still ran | The lock also names the child process | `test_lock_is_respected_while_the_training_child_is_alive` |

**Third review** (2026-10-20, of the fixes for the second review, commit
`3f9444f`): no critical findings. The 7 findings of the second review were
judged closed; the reviewer confirmed on this machine that a Windows folder
rename fails while a model file is open or memory-mapped, so the in-use fix
holds. It raised 2 important and 6 minor findings. All 8 are fixed except
the last minor one, which is recorded below:

| Finding | Fix | Test |
|---|---|---|
| Important: a `.txt` upload was read as CSV and each review cut at its first comma | `.csv` files are read as CSV, any other file one review per line | `Batch.review3.test.tsx` |
| Important: editing an uploaded CSV in the box switched it to one-review-per-line, so the header and ids were analysed | The mode changes only when the box is emptied or text goes into an empty box; a visible "Read the text as" switch shows and changes it | `Batch.review3.test.tsx` |
| Minor: two regression tests of the second review passed on the code before the fix | New tests that fail without the fix: a lock naming two dead processes is taken over; `execute_step` writes the child's id into the lock; `evaluate.main()` refuses `--limit` into `docs/` | `test_lock_naming_two_dead_processes_is_taken_over`, `test_lock_names_the_training_child_while_it_runs`, `test_limit_run_writing_into_docs_is_refused_by_main` |
| Minor: "needs decision" advised `run_all`, which does not evaluate the installed models while a slot is empty | The advice says to fill the empty slots with `promote --apply` first | `test_unevaluated_model_with_an_empty_slot_says_to_fill_it_first` |
| Minor: an installed folder without `training_log.json` is never repaired, though the recovery guide said so; a repair was silent | The verdict names the missing log and how to restore it; the guide says so; a repair is logged with where the incomplete copy went | `test_installed_model_without_a_training_log_is_named_as_such`, `test_apply_repairs_an_incomplete_installed_copy_and_says_so` |
| Minor: `promote --apply` stopped with a traceback when a model was in use | The error is logged per slot, the others are installed, exit code 4 | `test_apply_continues_past_a_model_in_use` |
| Minor: the DOCX export dropped every level-1 heading of an appendix | Only the first, which repeats the appendix title | `test_appendix_keeps_a_second_top_level_section` |

Each of these tests was run against the code before its fix and failed
there. The fixes for the third review were not reviewed again; they are
small and each is pinned by a failing-before test, so the review rounds
are closed.

Recorded as minor and not fixed:

- Tracked report files contain the local path `C:\Users\Admin\...` in the
  training logs, and `/api/model-info` serves it.
- No request-body size limit when running plain uvicorn.
- `clean_text` removes text between `<` and `>`; a review that is only a tag
  is stored as empty text.
- A batch chunk that fails after the server saved part of it is sent again by
  "Continue", which can duplicate those saved reviews.
- `requirements.txt` gives minimum versions only; there is no lock file.
- Two starters racing for a stale lock; models without a training log cannot
  be told apart by the staleness checks; an archive folder with the same
  second-resolution name would nest.
- `evaluate --domains laptops` without `--limit` overwrites the two-domain
  results (the real-model test then fails, which reveals it).
- Docker: the health check allows about 135 seconds for loading the models;
  the backend container runs as root.
- `ConfirmDialog` has no focus trap; an out-of-range `?page=` in History
  shows the empty message; the Analyzer reads the health status only once.
- The apostrophe that neutralises a formula stays visible in the exported CSV.
- The report's concluding sentences are fixed text and would not follow
  different numbers after a retrain.
- `run_all` writes the training child's id into the lock just after starting
  it, so a kill in that instant leaves a lock naming only the parent; `run`
  recognises the real step runner by identity rather than by a parameter.
  Both were judged acceptable by the third review.

## 4. Pending, by what each item is waiting for

**Awaiting the assignment brief**

1. Check section 1 against the real requirements. No brief, synopsis or
   marking scheme has been supplied; none was invented.
2. Names, roll numbers, course and supervisor on the report's title page and
   the title slide; the required template for the slides, if there is one.

**Awaiting an external backup**

3. Copy `absa-models.zip`, `absa-history.zip` and their `.sha256` files to
   another physical device or a cloud location, then verify there with
   `Get-FileHash <file> -Algorithm SHA256` against the `.sha256` files.
   This machine has a single disk; a OneDrive folder exists but nothing was
   uploaded to it.
4. Only after that: decide on removing the three model folders in
   `models/candidates` (1.22 GB) and `models/train_sentiment_aspect.log`.
   `models/previous` and `models/sentiment_joint_backup` are to be kept.

**Awaiting a remote repository**

5. Push the branch; the CI workflow has never run and is not claimed to pass.
6. Merge `feature/models-evaluation` into `main` after CI has run. The
   branch is intact and unmerged; the review rounds are closed (section 3).

**Awaiting a Docker environment**

7. `docker compose up --build`, open http://localhost:8080, analyse one
   review, check History and Dashboard. Until that succeeds Docker stays
   marked untested everywhere (README, report, this file).

**Can be done here, not done yet**

8. A person's own read of the DOCX and the slides.
9. Done 2026-10-21: browser check of the Batch page's "Read the text as"
   switch at 1366 px and 390 px, with the backend and models running. All
   steps passed; the only console error was the missing `/favicon.ico` (404).

## 5. Known limitations of the result

- Neutral is the weakest sentiment class, and sentences that mix sentiments
  are the hardest case (accuracy 0.6616 against 0.8507 for uniform sentences).
- One training run, one seed; the deployed models were chosen by comparing
  test scores, which makes the reported scores slightly optimistic.
- On hand-written reviews of other product categories the pipeline makes
  visible mistakes, for example "room" marked negative in "The room was
  spotless".
