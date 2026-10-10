# Aspect-Based Sentiment Analysis for Automated Product Review Analysis Using Natural Language Processing

Traditional sentiment analysis tells us whether a review is positive or
negative. This project goes further: it automatically finds the individual
product aspects mentioned in a review and determines the sentiment towards each
one, using fine-tuned BERT models.

```
"The screen is gorgeous and the keyboard feels great, but the battery life is terrible."

Traditional:   one label for the whole review
This project:  screen -> positive    keyboard -> positive    battery life -> negative
```

## Project status

| Part | Status |
|---|---|
| Dataset pipeline (SemEval-2014 Task 4) | Done |
| Aspect extraction model (BERT token classification, BIO tags) | Done |
| Aspect sentiment model (BERT sentence-pair classification) | Done |
| Overall sentiment model (traditional baseline) | Done |
| End-to-end ABSA pipeline | Done |
| Model evaluation on the test set | Done, see [docs/results.md](docs/results.md) |
| FastAPI backend + SQLite database | Done |
| Backend tests | Done |
| Frontend: analyzer, batch CSV analysis, history, dashboard | Done, see [frontend/README.md](frontend/README.md) |
| Frontend tests | Done |
| Non-BERT baseline, error analysis, transfer study | Done, see [docs/baseline.md](docs/baseline.md), [docs/error_analysis.md](docs/error_analysis.md), [docs/transfer.md](docs/transfer.md) |
| Notebooks | Done, see `notebooks/` |
| Project report and slides | Done, see [docs/report.md](docs/report.md), [docs/slides.md](docs/slides.md) |
| Docker setup | Written, **not yet run** (Docker is not installed on the development machine) |

Every module with its status and how it is tested:
[docs/PROJECT_CHECKLIST.md](docs/PROJECT_CHECKLIST.md). New to the project? Start
with [CONTRIBUTING.md](CONTRIBUTING.md).

## How it works

```
review -> preprocessing -> BERT aspect extraction -> aspect + context pairing
       -> BERT sentiment classification -> aspect-sentiment map + overall sentiment
       -> REST API -> database -> web interface
```

| Document | Content |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Components, request flow, database, design decisions |
| [docs/methodology.md](docs/methodology.md) | Dataset, preprocessing, models, training, metrics, limitations |
| [docs/results.md](docs/results.md) | Measured test-set results (generated, never hand-written) |
| [docs/API.md](docs/API.md) | Every endpoint with example requests and responses |
| [docs/baseline.md](docs/baseline.md) | BERT against a rule-and-lexicon baseline (generated) |
| [docs/error_analysis.md](docs/error_analysis.md) | Where the models go wrong (generated) |
| [docs/transfer.md](docs/transfer.md) | Laptop-trained models on restaurant reviews; other categories (generated) |
| [docs/report.md](docs/report.md), [docs/slides.md](docs/slides.md) | Project report and presentation (generated) |
| [docs/demo.md](docs/demo.md) | Five-minute demo script |
| [docs/model_sharing.md](docs/model_sharing.md) | How teammates get the trained models |

## Repository layout

```
backend/
  app/
    main.py              FastAPI application
    config.py            settings from environment variables
    api/routes/          analysis.py, reviews.py, health.py
    nlp/                 preprocessing, aspect_extraction, sentiment, pipeline
    models/              wrappers around the two BERT models
    database/            SQLAlchemy engine, tables, queries
    schemas/             request/response models (the API contract)
  training/              prepare_dataset, train_aspect, train_sentiment, evaluate,
                         run_all, promote, baseline, error_analysis, report
  tests/
frontend/
  src/services/api.ts    the connection point to the backend
  src/types/api.ts       response types
  src/lib/               pure helpers (highlighting, CSV, error messages)
  src/components/        result views, charts, dialogs
  src/pages/             Home, Analyzer, Batch, History, Dashboard
notebooks/               data exploration, preprocessing, model evaluation
data/                    dataset (downloaded), sample reviews, the SQLite database
models/                  three trained models (not in git) and the evaluation reports
  candidates/            output of training.run_all, before promotion (not in git)
  previous/              models replaced by a promotion (not in git)
docs/
docker-compose.yml
```

## Setup

Requirements: Python 3.10 or newer, Node.js 20 or newer. Commands are for
Windows PowerShell; on macOS/Linux use `source .venv/bin/activate`.

### 1. Backend environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r backend\requirements.txt
```

The first line installs the CPU build of PyTorch. With an NVIDIA GPU, install
the CUDA build from https://pytorch.org/get-started/locally/ instead.

### 2. Dataset

```powershell
cd backend
python -m training.prepare_dataset
```

### 3. Train the models

The three trained models are about 420 MB each and are not stored in git.
Either get the folders `models/aspect_extraction`, `models/sentiment` and
`models/overall_sentiment` from a teammate
([docs/model_sharing.md](docs/model_sharing.md)), or train them:

```powershell
python -m training.run_all --smoke    # whole chain on 32 sentences: a few minutes
python -m training.run_all            # train the three models on both domains
python -m training.promote            # compare with the installed models
python -m training.promote --apply    # install the ones that qualify
python -m training.evaluate           # write docs/results.md for the installed models
```

These are the commands that produced the shipped models. `run_all` trains into
`models/candidates`, can be interrupted and resumed, and never touches the
installed models. The training time of each shipped model is in
[docs/results.md](docs/results.md); expect several hours in total on a laptop
CPU (plugged in, lid open) and minutes on a GPU. Options and a Google Colab
recipe are in [backend/training/README.md](backend/training/README.md).

The analysis documents are regenerated with:

```powershell
python -m training.baseline           # docs/baseline.md
python -m training.error_analysis     # docs/error_analysis.md, docs/transfer.md
python -m training.report             # docs/report.md, docs/slides.md
```

### 4. Run the backend

```powershell
cd backend
uvicorn app.main:app --reload
```

- API: http://localhost:8000/api
- Interactive documentation: http://localhost:8000/docs

Try it:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/analyze -ContentType "application/json" -Body '{"review": "The screen is gorgeous but the battery life is terrible."}' | ConvertTo-Json -Depth 5
```

### 5. Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The header shows whether the backend is connected.
A guided run-through is in [docs/demo.md](docs/demo.md).

## Tests

```powershell
cd backend
pytest                  # everything; tests needing trained models skip if they are missing
pytest -m "not model"   # fast tests only (a few seconds)
```

```powershell
cd frontend
npm test                # component and helper tests
npm run build           # type-check and build
```

## Docker

`docker compose up --build` is meant to serve the application on
http://localhost:8080 with the models mounted from `./models`. **This setup has
not been run yet**: Docker is not installed on the development machine. Treat it
as a starting point until someone has tried it.

## Configuration

Optional. Copy `backend/.env.example` to `backend/.env`. Useful settings:

| Variable | Default | Purpose |
|---|---|---|
| `ABSA_LOAD_MODELS` | `true` | `false` starts the API without models (frontend work) |
| `ABSA_DATABASE_URL` | SQLite file in `data/` | Any SQLAlchemy URL |
| `ABSA_CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |
| `ABSA_LOG_LEVEL` | `INFO` | |

## Technology

Python, PyTorch, Hugging Face Transformers (`bert-base-uncased`), scikit-learn,
NLTK, pandas, FastAPI, Pydantic, SQLAlchemy, SQLite, React, TypeScript, Vite,
Tailwind CSS, Recharts.

## Dataset

SemEval-2014 Task 4: Aspect Based Sentiment Analysis (Pontiki et al., 2014).
See [data/README.md](data/README.md).
