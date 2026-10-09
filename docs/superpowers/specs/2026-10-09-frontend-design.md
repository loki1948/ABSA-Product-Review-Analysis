# Sub-project 2: Frontend application — design

Date: 2026-10-09. Status: written while sub-project 1 trains; implementation
starts after sub-project 1 is verified. Part 2 of 4, see
[../../PROJECT_CHECKLIST.md](../../PROJECT_CHECKLIST.md).

## 1. Goal

A person opens the site, pastes a product review, and sees which aspects the
review mentions, the sentiment towards each one, and the single overall label a
traditional system would give. They can look back at earlier reviews, see
aggregate charts, analyse a CSV file of reviews, and see how accurate the
models are. Every state the backend can be in has a clear screen.

Who it is for: the project's evaluators during a demo, and teammates who must
be able to read and extend the code.

Success:

1. No page prints raw JSON; `JsonPreview` and every `TODO(frontend team)`
   comment are gone.
2. Each row of section F of the checklist has a passing automated test, or a
   named manual check where automation is not meaningful (layout).
3. `npm run build` and `npm test` pass.
4. With the backend running on the models from sub-project 1, a review typed
   in the browser produces highlighted aspects and appears in History and the
   Dashboard.

## 2. Constraints carried over from the existing code

- React 19, TypeScript strict, Vite, Tailwind CSS 4, Recharts, React Router.
  No new runtime dependency. Development dependencies added: Vitest, jsdom,
  React Testing Library, `@testing-library/user-event`,
  `@testing-library/jest-dom`.
- Components never call `fetch`; they call `src/services/api.ts`.
- `src/types/api.ts` mirrors `backend/app/schemas/analysis.py`.
- The backend API does not change in this sub-project.
- Sentiment is never shown by colour alone: every coloured element also has a
  text label, so the interface works for colour-blind readers and in print.

## 3. Structure

```
src/
  lib/
    sentiment.ts       labels, colour classes and chart colours per sentiment; percent formatting
    highlight.ts       split a review into plain and aspect segments from start/end offsets
    csv.ts             parse an uploaded CSV into reviews; build a CSV from results
    modelReport.ts     typed, defensive reader for the /model-info report
  components/
    ReviewInput.tsx        text area, character count, example buttons, save toggle, submit
    SentimentBadge.tsx     coloured pill with the sentiment word
    SentimentCard.tsx      overall sentiment and confidence ("traditional" view)
    HighlightedReview.tsx  the review with aspects marked
    AspectTable.tsx        aspect, sentiment, confidence, context
    AspectSentimentChart.tsx   per-review counts of positive / negative / neutral aspects
    AnalysisResult.tsx     composes the five above for one AnalysisResponse
    StateMessage.tsx       loading, empty and error boxes used by every page
    Pagination.tsx
    ConfirmDialog.tsx
    ModelPerformance.tsx   metrics table from the report
    charts/                SentimentDistribution, AspectFrequency, AspectSentimentBars
  pages/
    Home.tsx  Analyzer.tsx  History.tsx  Dashboard.tsx  Batch.tsx
```

Each `lib` file is pure and unit-tested. Each component takes data through
props and has no knowledge of the network; pages own the calls.

## 4. Pages

### 4.1 Analyzer (`/analyze`)

Review-input workflow:

- Text area limited to 5000 characters, with a live count (`123 / 5000`).
- Three example buttons: a laptop review, a restaurant review, and a
  mixed-sentiment review. They fill the text area.
- "Save to history" checkbox, on by default, mapped to the request's `save`.
- The submit button is disabled while the text is blank or a request is in
  flight, and reads "Analyzing…" during the request. Ctrl+Enter submits.
- The previous result stays visible but dimmed while a new request runs.

Result, composed by `AnalysisResult`:

1. **Traditional view**: `SentimentCard` with the overall label and confidence.
2. **Aspect-based view**: `HighlightedReview`, then `AspectTable`, then
   `AspectSentimentChart`.
3. A one-sentence comparison generated from the data, for example "A
   traditional system reports *neutral*. Aspect-based analysis finds 2 positive
   and 1 negative aspect." When all aspects agree with the overall label, it
   says so instead.

Empty state: when `aspects` is empty, the aspect-based view is replaced by "No
product aspects were found in this review", and the overall sentiment is still
shown.

### 4.2 Error handling (all pages)

`ApiError.status` selects the message; `StateMessage` renders it with
`role="alert"`.

| Condition | What the user sees |
|---|---|
| status 0 (backend unreachable) | "Cannot reach the backend." plus the command to start it; a Retry button |
| 503 (models not loaded) | "The models are not loaded." plus the reason from `/api/health`; history and dashboard keep working |
| 422 (invalid input) | the validation message next to the input |
| 404 | "This review no longer exists." (History) |
| 500 and anything else | "Something went wrong on the server." with Retry |

The Analyzer disables its submit button, with an explanation, when
`/api/health` reports that the models are not loaded.

### 4.3 History (`/history`)

Table of stored reviews, newest first: date, review (truncated), overall
sentiment, number of aspects. Controls: sentiment filter (all, positive,
negative, neutral), page size 10, previous/next with "11–20 of 37". Clicking a
row expands it to the full `AnalysisResult`. Delete asks for confirmation, then
reloads the current page; if that page is now empty it moves one page back.
Filter and page are kept in the URL query so a reload keeps the view.

### 4.4 Dashboard (`/dashboard`)

Four summary numbers (reviews, aspect mentions, share of positive reviews,
share of positive aspects), then three charts from `/api/statistics`:
overall-sentiment distribution, the ten most frequent aspects, and a stacked
positive/neutral/negative bar per aspect. Below them, `ModelPerformance` from
`/api/model-info`: per test domain, aspect-extraction precision/recall/F1,
aspect-sentiment accuracy and macro-F1, accuracy on mixed sentences, overall
sentiment accuracy and macro-F1, end-to-end F1, and the training domains and
generation time. The card shows "No evaluation report yet" on 404 and never
breaks the rest of the page.

### 4.5 Batch (`/batch`)

Upload a `.csv` file or paste one review per line. The parser accepts a file
with a header containing a `review` or `text` column, or a single-column file
without a header; quoted fields with commas and line breaks are supported.
Rows that are blank or over 5000 characters are listed as skipped, with their
line numbers. At most 500 reviews per file.

Reviews are sent in chunks of 10 through `analyzeReviews`, one chunk at a time,
with a progress bar and a Cancel button. A failed chunk stops the run and keeps
the results already received. Results appear in a table (review, overall
sentiment, aspects as badges) and can be downloaded as CSV with one row per
aspect: `review, overall_sentiment, aspect, sentiment, confidence`.

Chunking in the browser is chosen over a new upload endpoint because the batch
endpoint already exists, analysis takes roughly a second per review on a CPU,
and small requests give real progress and avoid proxy timeouts.

### 4.6 Home (`/`)

What the project does in two paragraphs, a fixed worked example rendered with
the real result components (so it needs no backend), the three-step pipeline,
and links to the Analyzer and the Dashboard.

### 4.7 Shell

The header adds "Batch" to the navigation and keeps the connection indicator.
The layout is a single column under 640 px wide; tables scroll horizontally
inside their own container; charts use `ResponsiveContainer`.

## 5. Testing

Vitest with jsdom and React Testing Library. `services/api.ts` is mocked in
component tests; `fetch` is mocked in the client's own tests.

| Unit | Cases |
|---|---|
| `highlight.ts` | no aspects; aspect at start, middle, end; adjacent aspects; offsets outside the text or overlapping are ignored, not crashed on |
| `csv.ts` | header with `review`; header with `text`; no header; quoted commas and newlines; blank and over-long rows reported with line numbers; 500-row cap; export round-trip with quotes |
| `modelReport.ts` | full two-domain report; report without per-domain scopes; missing sections give "n/a", not an exception |
| `api.ts` | 204; string `detail`; 422 list `detail`; network failure gives status 0 |
| `ReviewInput` | count updates; blank disables submit; example fills text; Ctrl+Enter submits; save toggle value |
| `AnalysisResult` | highlights each aspect; table rows; comparison sentence for mixed and for uniform results; empty-aspects state |
| Analyzer page | success; each row of the error table in 4.2; disabled when models are not loaded |
| History page | renders rows; filter changes the request; pagination; delete confirmed and cancelled; empty state |
| Dashboard page | summary numbers; empty state when there are no reviews; model card on 404 |
| Batch page | parse, chunked calls in order, progress, cancel, failed chunk keeps earlier results, export |

Manual checks, recorded in the checklist when done: phone width (375 px) and
desktop width for every page; keyboard-only run through the Analyzer; one
end-to-end session against the real backend (analyse, see it in History, see
the Dashboard change, delete it).

## 6. Out of scope

Authentication, dark mode, internationalisation, editing stored reviews, a
server-side upload endpoint, and browser end-to-end automation (Playwright).
