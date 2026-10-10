# Team guide

How to get the project running on your machine, how it is organised, and what
is open to work on.

## 1. Get it running (about 15 minutes, plus model training)

Follow "Setup" in the [README](README.md). The short version:

1. Create the Python environment and install the backend requirements.
2. `python -m training.prepare_dataset` (downloads the dataset, under a minute).
3. Get the three trained models. They are about 420 MB each and are not in git, so either
   - get them from a teammate ([docs/model_sharing.md](docs/model_sharing.md)), or
   - train them yourself (see "Train the models" in the README; minutes on a
     GPU such as free Google Colab, several hours on a laptop CPU).
4. Start the backend, then the frontend.

Frontend-only work does not need the models: start the backend with
`ABSA_LOAD_MODELS=false`.

## 2. Read these first

| To understand | Read |
|---|---|
| The whole system and the request flow | [docs/architecture.md](docs/architecture.md) |
| Dataset, BIO tagging, the two models, metrics | [docs/methodology.md](docs/methodology.md) |
| What the models actually score | [docs/results.md](docs/results.md) |
| Every endpoint with example JSON | [docs/API.md](docs/API.md) |
| The frontend | [frontend/README.md](frontend/README.md) |

A good way into the code is to follow one request:
`backend/app/api/routes/analysis.py` -> `backend/app/nlp/pipeline.py` -> the
three modules it calls. All of it is commented.

## 3. What is done

- Dataset download, validation and train/validation/test split.
- Preprocessing, BIO conversion, word-piece label alignment.
- Three BERT models trained on both domains; `training.run_all` and
  `training.promote` retrain and install them safely; `training.evaluate`
  generates `docs/results.md`.
- A rule-and-lexicon baseline, an error analysis and a transfer study, each
  generating its own document; three notebooks.
- FastAPI backend with SQLite storage: analyze (single and batch), history,
  statistics, health, model info.
- Frontend: analyzer, batch CSV analysis, history, dashboard, home page, with
  loading, error and empty states.
- Tests for backend and frontend.
- Project report and slides, generated from the evaluation outputs.

The full list, with how each part is tested, is in
[docs/PROJECT_CHECKLIST.md](docs/PROJECT_CHECKLIST.md).

## 4. Open work

Pick one, tell the team, create a branch.

### Delivery

- [ ] Run the Docker setup (`docker compose up --build`) on a machine with
      Docker and fix whatever it reveals. It has never been run.
- [ ] Continuous integration: run `pytest -m "not model"`, `npm test` and
      `npm run build` on every push.
- [ ] Export the slides (`docs/slides.md`, Marp format) to the format the
      presentation needs, and add screenshots.

### NLP and evaluation

- [ ] Improve accuracy on mixed-sentiment sentences (see the "mixed" row in
      `docs/results.md`): more training data with contrasting aspects, or
      marking the aspect's position in the input.
- [ ] Train with several seeds and report mean and spread.
- [ ] Annotated test data for another product category, to turn the
      illustration in `docs/transfer.md` into a measurement.
- [ ] A learnt non-BERT baseline (for example a CRF tagger) next to the
      rule-based one.

### Frontend

- [ ] Split the Dashboard into its own bundle (Recharts makes the first load
      larger than it needs to be).
- [ ] Browser end-to-end tests (for example Playwright).

## 5. Working together

- `main` should always run. Work on a branch (`feature/history-page`), open a
  pull request, have one teammate look at it.
- Before pushing: `pytest` in `backend/`, `npm test` and `npm run build` in `frontend/`.
- **The API contract is shared.** If a response changes, update
  `backend/app/schemas/analysis.py`, `frontend/src/types/api.ts` and
  `docs/API.md` in the same commit, and tell whoever is building the UI.
- **Never write a metric by hand.** Numbers in the report come from
  `docs/results.md` / `models/evaluation_report.json`, which only
  `training/evaluate.py` writes. If you retrain, rerun it and commit the result.
- Do not commit `models/*/`, `data/raw`, `data/processed`, `.env`,
  `node_modules` or `.venv` (already in `.gitignore`).
- Do not add a hard-coded aspect list or an external sentiment API to the main
  pipeline. The project's claim is that both steps are learnt models.

## 6. Conventions

- Python: type hints on every function, a docstring where the purpose is not
  obvious, `logging` instead of `print` in application code.
- Tests live in `backend/tests`. Fast tests use the stub models in
  `conftest.py`; tests that need the real models carry `@pytest.mark.model` and
  are skipped when the models are absent.
- TypeScript: strict mode; no `fetch` outside `src/services/api.ts`.
