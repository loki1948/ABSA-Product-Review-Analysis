# Full-project checklist

Status of every module on 2026-10-10, with the evidence for it. Status is
**Completed** (built and verified as described), **Partial** (built, with a
named gap) or **Pending**.

**The project is not 100% complete.** Section J lists what is still open.

## A. Data

| Module | Status | Evidence |
|---|---|---|
| Dataset download, validation, split, leakage check | Completed | `tests/test_dataset.py`; notebook 01 repeats the leakage check (0 shared sentences) |
| Dataset statistics | Completed | `data/processed/dataset_stats.json`; tables in notebook 01 and the report |
| Sample reviews for demo and transfer illustration | Completed | `data/samples/demo_reviews.csv`, `data/samples/other_domains.csv` |

## B. NLP core

| Module | Status | Evidence |
|---|---|---|
| Preprocessing: cleaning, sentences, tokens, BIO, context | Completed | `tests/test_preprocessing.py`; notebook 02. Fixed: punctuation-only fragments ("!!") no longer count as sentences |
| Aspect extraction, sentiment, pipeline | Completed | `tests/test_aspect.py`, `test_sentiment.py`, `test_pipeline.py`, including 7 tests on the real models |

## C. Models (sub-project 1)

| Module | Status | Evidence |
|---|---|---|
| Aspect-extraction model, both domains | Completed | `models/aspect_extraction/training_log.json`: best epoch 3, validation F1 0.8312. Test F1 0.8462 |
| Aspect-sentiment model, both domains | Completed | best epoch 3, validation macro-F1 0.7574. Test accuracy 0.8151, macro-F1 0.7456 |
| Overall-sentiment model, both domains | Completed | best epoch 4, validation macro-F1 0.7363. Test macro-F1 0.7202 (weak labels) |
| Resumable training chain (`training/run_all.py`) | Completed | 14 tests; smoke run passed in 3 min 17 s; full run finished 2026-10-10 09:30 |
| Comparison and promotion (`training/promote.py`) | Completed | 12 tests; all three candidates met the rule on laptops and restaurants; the comparison is reproduced by `python -m training.promote`; the laptops-only side is in `docs/transfer.md` |
| Previous models preserved | Completed | `models/previous/aspect_extraction-20261010-093116`, `models/previous/sentiment-20261010-093116`; `models/sentiment_joint_backup` and `models/train_sentiment_aspect.log` unchanged; `models/candidates` kept |

## D. Evaluation (sub-project 1)

| Module | Status | Evidence |
|---|---|---|
| `docs/results.md`, `models/evaluation_report.json` | Completed | Generated 2026-10-10 from the deployed models, both domains, with the mixed-sentence breakdown |
| Two confusion-matrix figures | Completed | `docs/figures/sentiment_confusion_matrix.png`, `overall_confusion_matrix.png` |
| Report describes the deployed models | Completed | `test_report_describes_the_deployed_models` passes; `/api/model-info` returned both domains in the browser test |
| Real-model tests | Completed | `pytest`: 120 passed, 0 skipped, 0 failed (was 10 skipped) |

## E. Backend API

| Module | Status | Evidence |
|---|---|---|
| Analyze (single, batch), history, statistics, health, model info | Completed | `tests/test_api.py` (stubs) plus two tests through the real models; exercised from the browser |
| Validation and error shape, storage, configuration, CORS | Completed | `tests/test_api.py`, `tests/test_database.py` |

## F. Frontend (sub-project 2)

Automated: `npm test` 87 passed; `npm run build` passes. Browser: one session
on 2026-10-10 in Chrome against the real backend and models, driven by script
(DOM events and DOM reads; see "Not verified" below).

| Module | Status | Evidence |
|---|---|---|
| Review-input workflow (examples, counter, blank guard, save toggle, Ctrl+Enter) | Completed | `ReviewInput.test.tsx`; browser: blank input disables the button, 5000-character limit applied |
| Overall sentiment and aspect-level results, highlighting, per-review chart, comparison sentence | Completed | `AnalysisResult.test.tsx`; browser: laptop review gave screen and keyboard positive, battery life negative; restaurant review gave pasta and staff positive, prices negative |
| Empty state (no aspects) | Completed | Test; browser: "It arrived on Tuesday." shows the no-aspects message and still shows the overall label |
| Error handling: backend unreachable, models not loaded, invalid input, server error | Completed | `Analyzer.test.tsx`, `App.test.tsx`; browser: both states checked on every page. Found and fixed: behind the dev proxy a stopped backend answers HTTP 502, which was shown as a server error |
| History: list, pagination, filter, full analysis, delete with confirmation | Completed | `History.test.tsx`; browser: 15 reviews paged 10 + 5, negative filter, expand, cancel, delete |
| Dashboard: summary, three charts, model performance | Completed | `Dashboard.test.tsx`; browser: charts drawn, aspects grouped ("prices" counted under "price"), model table shows the three test sets |
| Batch: paste or CSV, chunks of ten, progress, cancel, export | Partial | `Batch.test.tsx` (7 tests incl. file upload, cancel, failed chunk, export); browser: 12 reviews analysed in two requests (10 + 2). The file picker and the CSV download were not exercised in the browser |
| Home page, navigation, not-found page | Completed | `App.test.tsx` |
| Responsive layout, keyboard use | Partial | No sideways overflow at 1366 px on any page. **Phone width not verified** (the browser window would not resize); keyboard-only run not done |
| Screenshots | Pending | Screenshot capture timed out in the test browser |

## G. NLP analysis (sub-project 3)

| Module | Status | Evidence |
|---|---|---|
| Rule-and-lexicon baseline | Completed | 14 tests; `docs/baseline.md`: aspect F1 0.3765 against 0.8462 for BERT, end-to-end F1 0.2530 against 0.6977 |
| Error analysis | Completed | 7 tests; `docs/error_analysis.md` generated from the deployed models |
| Cross-domain transfer (measured) | Completed | `docs/transfer.md`: laptops-only models on restaurants, aspect F1 0.3704 against 0.8715 |
| Other product categories | Partial | Twelve hand-written reviews in `docs/transfer.md`, as an illustration only. No annotated data, so no accuracy figure |
| Notebooks 01, 02, 03 | Completed | Each executed top to bottom with `jupyter nbconvert --execute`, no error cells |

## H. Documentation

| Module | Status | Evidence |
|---|---|---|
| README, CONTRIBUTING, frontend README, training README | Completed | Describe the commands that were run and the current state |
| Architecture, methodology, API | Completed | Methodology and API updated for the two-domain models |
| Project report | Completed | `docs/report.md`, generated by `training/report.py` (6 tests); every number read from the evaluation outputs |
| Slides | Partial | `docs/slides.md` (Marp markdown, 14 slides), generated from the same numbers. Not exported to PowerPoint or PDF; no screenshots |
| Demo script | Completed | `docs/demo.md`; its steps match what was tested in the browser |
| Model sharing guide | Completed | `docs/model_sharing.md` |

## I. Delivery (sub-project 4)

| Module | Status | Evidence |
|---|---|---|
| Git history | Completed | Branch `feature/models-evaluation`; no weights, datasets or env files tracked |
| `Dockerfile`s and `docker-compose.yml` | Partial | Written. **Never run**: Docker is not installed on the development machine |
| Model distribution to teammates | Partial | Procedure documented; the archive has not been created or shared |
| Continuous integration | Pending | Needs a remote repository |

## J. Still open

1. Run the Docker setup on a machine with Docker.
2. Check the interface at phone width and with the keyboard only; try the file
   picker and the CSV download by hand; take screenshots.
3. Export the slides to the format the presentation requires.
4. Merge `feature/models-evaluation` into `main`; add a remote; set up CI.
5. Create and share the model archive.
6. Decide what to do with `models/candidates`, `models/previous`,
   `models/sentiment_joint_backup` and `models/train_sentiment_aspect.log`
   (about 3.5 GB). Nothing has been deleted.
7. Independent code review of the branch.

## Open questions

1. The docs mention "the project plan", but no synopsis or marking scheme is
   in the repository. Add it so this checklist can be checked against it.
2. Required format, template and length of the report and the slides.
3. Is annotated data for another product category available?

## Known limitations of the result

- Neutral is the weakest sentiment class and sentences that mix sentiments are
  the hardest case (accuracy 0.6616 against 0.8507 for uniform sentences).
- One training run, one seed. The deployed models were chosen by comparing
  test scores, which makes the reported scores slightly optimistic.
- In the illustration on other product categories the pipeline made visible
  mistakes, for example "room" marked negative in "The room was spotless".
