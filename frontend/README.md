# Frontend

React + TypeScript + Vite + Tailwind CSS, with Recharts for the dashboard
charts.

## Run

```
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Start the backend first (see the root README). The dot in the page header shows
whether the frontend reaches it. To work on the UI without trained models, start
the backend with `ABSA_LOAD_MODELS=false`: history, statistics and the dashboard
work, and the Analyzer explains that the models are not loaded.

## Check your work

```
npm test             # all tests once (Vitest + React Testing Library)
npm run test:watch   # rerun on save
npm run build        # type-check and production build
```

Run `npm test` and `npm run build` before pushing.

## Pages

| Page | Route | What it does |
|---|---|---|
| Home | `/` | Explains the idea with a fixed worked example |
| Analyzer | `/analyze` | One review in; overall sentiment, highlighted aspects, aspect table out |
| Batch | `/batch` | CSV upload or one review per line; progress, results table, CSV export |
| History | `/history` | Saved reviews: filter by sentiment, pagination, full analysis, delete |
| Dashboard | `/dashboard` | Summary numbers, three charts, and the models' test-set metrics |

## How the code is organised

```
src/
  services/api.ts   the only file that calls fetch; one function per endpoint
  types/api.ts      response types, mirroring backend/app/schemas/analysis.py
  hooks/useApi.ts   load data on mount: { data, failure, loading, reload }
  lib/              pure functions, no React: easy to read and to test
    highlight.ts      review + aspect offsets -> plain and marked segments
    csv.ts            parse an uploaded CSV, build the export CSV
    modelReport.ts    read the evaluation report defensively
    errors.ts         failed request -> title and message for the user
    sentiment.ts      label, colours and percent formatting per sentiment
  components/       receive data through props; never call the API
  pages/            one file per route; pages own the API calls
```

```
component  ->  src/services/api.ts  ->  /api/...  ->  Vite dev proxy  ->  FastAPI :8000
```

Full endpoint reference with example JSON: [`docs/API.md`](../docs/API.md).

## Conventions

- **No `fetch` outside `src/services/api.ts`.** Every failure is thrown as an
  `ApiError` with a `status`; `describeError` turns it into the message shown.
- **Every view handles three states**: loading, error (with "Try again" where a
  retry can help) and empty. Use `<StateMessage>`.
- **Colour is never the only signal.** A sentiment always appears as a word as
  well, and each chart carries a text description (`aria-label`).
- **Tests sit next to the code** (`Thing.tsx` and `Thing.test.tsx`). Component
  tests mock `services/api`; write the test first and watch it fail.
- When a response changes, update `backend/app/schemas/analysis.py`,
  `src/types/api.ts` and `docs/API.md` in the same commit.

## Limits worth knowing

- A review is at most 5000 characters (same as the backend).
- Batch analysis sends 10 reviews per request and reads at most 500 reviews
  from one file. A failed request stops the run and keeps the results so far.
- History shows 10 reviews per page; the dashboard shows the 10 most frequent
  aspects.
