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
| Frontend connection point (typed API client, wired scaffold) | Done |
| Frontend pages, charts, dashboard | **Open**, see [CONTRIBUTING.md](CONTRIBUTING.md) |

New to the project? Start with [CONTRIBUTING.md](CONTRIBUTING.md).

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
  training/              prepare_dataset, train_aspect, train_sentiment, evaluate
  tests/
frontend/
  src/services/api.ts    the connection point to the backend
  src/types/api.ts       response types
  src/pages/             Home, Analyzer, History, Dashboard (scaffold)
data/                    dataset (downloaded) and the SQLite database
models/                  three trained models (not in git) and evaluation_report.json
docs/
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
Either copy the folders `models/aspect_extraction`, `models/sentiment` and
`models/overall_sentiment` from a teammate, or train them:

```powershell
python -m training.train_aspect --domains laptops
python -m training.train_sentiment --task aspect
python -m training.train_sentiment --task overall --epochs 3
python -m training.evaluate
```

These are the commands that produced the shipped models. They take about 2.5
hours in total on a laptop CPU and a few minutes on a GPU. Options and a Google
Colab recipe are in [backend/training/README.md](backend/training/README.md).

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

## Tests

```powershell
cd backend
pytest                  # everything; tests needing trained models skip if they are missing
pytest -m "not model"   # fast tests only (a few seconds)
```

```powershell
cd frontend
npm run build           # type-check and build
```

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
