# Team guide

How to get the project running on your machine, how it is organised, and what
is open to work on.

## 1. Get it running (about 15 minutes, plus model training)

Follow "Setup" in the [README](README.md). The short version:

1. Create the Python environment and install the backend requirements.
2. `python -m training.prepare_dataset` (downloads the dataset, under a minute).
3. Get the three trained models. They are about 420 MB each and are not in git, so either
   - copy the folders `models/aspect_extraction`, `models/sentiment` and
     `models/overall_sentiment` from a teammate who has trained them (a shared
     drive works well), or
   - train them yourself (see "Train the models" in the README; minutes on a
     GPU such as free Google Colab, about 2.5 hours on a laptop CPU).
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
| The frontend scaffold | [frontend/README.md](frontend/README.md) |

A good way into the code is to follow one request:
`backend/app/api/routes/analysis.py` -> `backend/app/nlp/pipeline.py` -> the
three modules it calls. All of it is commented.

## 3. What is done

- Dataset download, validation and train/validation/test split.
- Preprocessing, BIO conversion, word-piece label alignment.
- Training scripts for the three BERT models; evaluation script that generates
  `docs/results.md`.
- End-to-end ABSA pipeline.
- FastAPI backend with SQLite storage: analyze (single and batch), history,
  statistics, health.
- Tests for preprocessing, dataset code, metrics, pipeline, database and API.
- Frontend scaffold: typed API client, routing, pages that fetch and display raw
  data.

## 4. Open work

Pick one, tell the team, create a branch.

### Frontend (main open area)

Details and the data each page already receives are in
[frontend/README.md](frontend/README.md).

- [ ] Home page.
- [ ] Analyzer results: overall-sentiment card, aspect table with confidence,
      aspects highlighted inside the review text.
- [ ] Per-review sentiment chart.
- [ ] History page: list, pagination, sentiment filter, delete.
- [ ] Dashboard: sentiment distribution, aspect frequency, sentiment per aspect
      (Recharts).
- [ ] Model-performance card from `GET /api/model-info`.
- [ ] Loading, error and empty states; responsive layout.
- [ ] Frontend tests (for example Vitest + React Testing Library).

### NLP and evaluation

- [ ] Retrain on a GPU with both domains and more epochs; compare with the
      current results (`python -m training.evaluate` regenerates the tables).
- [ ] Improve accuracy on mixed-sentiment sentences (see the "mixed" row in
      `docs/results.md`): more training data with contrasting aspects, or
      marking the aspect's position in the input.
- [ ] Baseline for the report: a non-BERT method (for example noun-phrase
      extraction + a sentiment lexicon) evaluated with the same script, to
      quantify what BERT adds.
- [ ] Error analysis notebook: which aspects are missed, which sentiments are
      confused (the neutral class is the usual weak spot).
- [ ] Notebooks from the plan: `01_data_exploration`, `02_preprocessing`,
      `03_model_evaluation`.
- [ ] Try the pipeline on reviews from another product category and document
      how well it transfers.

### Backend and delivery

- [x] Batch endpoint: `POST /api/analyze/batch` (up to 50 reviews).
- [ ] CSV upload page in the frontend that calls the batch endpoint.
- [ ] `docker-compose.yml` for backend + frontend.
- [ ] Project report and slides, built from `docs/`.

## 5. Working together

- `main` should always run. Work on a branch (`feature/history-page`), open a
  pull request, have one teammate look at it.
- Before pushing: `pytest` in `backend/`, `npm run build` in `frontend/`.
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
