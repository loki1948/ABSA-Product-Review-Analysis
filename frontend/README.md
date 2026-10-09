# Frontend

React + TypeScript + Vite + Tailwind CSS. Recharts is installed for the charts.

## Run

```
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Start the backend first (see the root README). The dot in the page header shows
whether the frontend reaches it. To work on the UI without trained models, start
the backend with `ABSA_LOAD_MODELS=false`: history and statistics work, only
"Analyze" answers with an error.

`npm run build` type-checks and builds; run it before pushing.

## How the frontend talks to the backend

```
component  ->  src/services/api.ts  ->  /api/...  ->  Vite dev proxy  ->  FastAPI :8000
```

- `src/services/api.ts`: one function per endpoint. Components never call
  `fetch` directly. Every failure is thrown as an `ApiError` whose `message` can
  be shown to the user.
- `src/types/api.ts`: TypeScript types of every response. They mirror
  `backend/app/schemas/analysis.py`.
- `src/hooks/useApi.ts`: `const { data, error, loading, reload } = useApi(() => getStatistics())`.
- Full endpoint reference with example JSON: [`docs/API.md`](../docs/API.md).

## What exists and what is open

The scaffold proves the connection: every page already fetches its data and
prints it with `<JsonPreview>`. The actual interface is still to be built.

| Page | File | Data source | To build |
|---|---|---|---|
| Home | `pages/Home.tsx` | none | Project explanation, traditional vs. aspect-based comparison, example review |
| Analyzer | `pages/Analyzer.tsx` | `analyzeReview()` (wired) | Overall-sentiment card, aspect table (aspect, sentiment, confidence %, context), aspects highlighted in the review using `start`/`end`, per-review chart |
| History | `pages/History.tsx` | `getReviews()` (wired) | List or table, pagination (`limit`/`offset`), sentiment filter, delete via `deleteReview()` |
| Dashboard | `pages/Dashboard.tsx` | `getStatistics()` (wired) | Sentiment distribution, aspect frequency, stacked positive/negative/neutral bar per aspect; model metrics card from `getModelInfo()` |

Suggested components (from the project plan): `ReviewInput`, `SentimentCard`,
`AspectTable`, `SentimentChart`. Delete `components/JsonPreview.tsx` once
nothing uses it.

Things to handle in every view: loading state, error state (`ApiError.message`),
and empty state (no aspects found, no history yet).
