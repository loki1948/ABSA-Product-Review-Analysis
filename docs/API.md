# REST API

Base URL in development: `http://localhost:8000/api`. Everything is JSON.
Interactive documentation (generated from the code) is served at
`http://localhost:8000/docs` while the backend runs.

The response models live in `backend/app/schemas/analysis.py`; the frontend
mirrors them in `frontend/src/types/api.ts` and calls every endpoint through
`frontend/src/services/api.ts`. Change all three together with this file.

| Method | Path | Purpose | Frontend function |
|---|---|---|---|
| POST | `/analyze` | Analyse one review | `analyzeReview` |
| POST | `/analyze/batch` | Analyse up to 50 reviews | `analyzeReviews` |
| GET | `/reviews` | Review history, newest first | `getReviews` |
| GET | `/reviews/{id}` | One stored review | `getReview` |
| DELETE | `/reviews/{id}` | Delete a stored review | `deleteReview` |
| GET | `/statistics` | Aggregates for the dashboard | `getStatistics` |
| GET | `/health` | Are the models and database up? | `getHealth` |
| GET | `/model-info` | Test-set metrics of the models | `getModelInfo` |

## Errors

Every error has the same shape, with a message that can be shown to the user:

```json
{ "detail": "Review not found." }
```

| Status | When |
|---|---|
| 404 | Unknown review id; no evaluation report yet |
| 422 | Invalid input. `detail` is then a list of `{ "loc": [...], "msg": "...", "type": "..." }` |
| 500 | Unexpected server error |
| 503 | The models are not loaded (not trained yet, or `ABSA_LOAD_MODELS=false`) |

## POST /analyze

Runs the ABSA pipeline on one review.

Request:

| Field | Type | Default | Notes |
|---|---|---|---|
| `review` | string | required | 1 to 5000 characters, not blank |
| `save` | boolean | `true` | `false` analyses without storing the result |

```json
{ "review": "The camera is excellent but the battery life is poor.", "save": true }
```

Response `200` (the sentiments and confidences shown here are illustrative):

```json
{
  "id": 1,
  "review": "The camera is excellent but the battery life is poor.",
  "overall_sentiment": "neutral",
  "overall_confidence": 0.61,
  "aspects": [
    {
      "aspect": "camera",
      "sentiment": "positive",
      "confidence": 0.97,
      "context": "The camera is excellent",
      "start": 4,
      "end": 10
    },
    {
      "aspect": "battery life",
      "sentiment": "negative",
      "confidence": 0.95,
      "context": "the battery life is poor.",
      "start": 32,
      "end": 44
    }
  ],
  "created_at": "2026-10-05T18:30:00+00:00"
}
```

| Field | Notes |
|---|---|
| `id` | History id; `null` when the request had `save: false` |
| `review` | The text that was analysed, whitespace-normalised. Offsets refer to this string |
| `overall_sentiment` | `positive`, `negative` or `neutral`, from the whole-sentence model |
| `overall_confidence` | 0 to 1 |
| `aspects[].aspect` | Aspect term exactly as written in the review |
| `aspects[].sentiment` | `positive`, `negative` or `neutral` |
| `aspects[].confidence` | Probability of the predicted sentiment, 0 to 1 |
| `aspects[].context` | Clause of the review that talks about the aspect |
| `aspects[].start`, `end` | Character offsets in `review`, `end` exclusive: `review.slice(start, end) === aspect` |
| `created_at` | ISO-8601 UTC timestamp; `null` when not saved |

`aspects` is an empty list when the review mentions no aspect.

## POST /analyze/batch

Analyses several reviews in one request. Reviews are processed one after the
other, so the response time grows with the number of reviews.

Request:

| Field | Type | Default | Notes |
|---|---|---|---|
| `reviews` | string[] | required | 1 to 50 reviews, each 1 to 5000 characters and not blank |
| `save` | boolean | `true` | `false` analyses without storing the results |

```json
{ "reviews": ["The camera is excellent.", "The battery life is poor."], "save": true }
```

Response `200`: `items` holds one `/analyze` response per review, in request
order.

```json
{ "total": 2, "items": [ { "id": 1, "...": "..." }, { "id": 2, "...": "..." } ] }
```

If any review is invalid the whole request is rejected with `422` and nothing
is analysed or stored.

## GET /reviews

Stored reviews, newest first.

| Query parameter | Default | Notes |
|---|---|---|
| `limit` | 20 | 1 to 100 |
| `offset` | 0 | For pagination |
| `sentiment` | none | `positive`, `negative` or `neutral`: filter by overall sentiment |

Response `200`:

```json
{ "total": 37, "limit": 20, "offset": 0, "items": [ { "id": 37, "...": "..." } ] }
```

`total` is the number of reviews matching the filter (not the page size);
each item has the `/analyze` response shape.

## GET /reviews/{id}

Response `200`: one stored review in the `/analyze` response shape. `404` if
the id does not exist.

## DELETE /reviews/{id}

Deletes the review and its aspects. Response `204` with no body; `404` if the
id does not exist.

## GET /statistics

Aggregates over the whole review history.

| Query parameter | Default | Notes |
|---|---|---|
| `top_n` | 10 | 1 to 50: how many of the most frequent aspects to return |

Response `200`:

```json
{
  "total_reviews": 4,
  "total_aspects": 5,
  "overall_sentiment_distribution": { "positive": 2, "negative": 2, "neutral": 0 },
  "aspect_sentiment_distribution": { "positive": 3, "negative": 2, "neutral": 0 },
  "top_aspects": [
    { "aspect": "battery", "total": 3, "positive": 2, "negative": 1, "neutral": 0 },
    { "aspect": "camera", "total": 2, "positive": 1, "negative": 1, "neutral": 0 }
  ]
}
```

`overall_sentiment_distribution` counts reviews; `aspect_sentiment_distribution`
counts aspect mentions. In `top_aspects` the aspect is normalised (lowercase,
singular), so "Battery" and "batteries" are counted together. The list is
sorted by `total`, most frequent first.

## GET /health

Always answers `200`, also when the service is degraded.

```json
{ "status": "ok", "models_loaded": true, "database": true, "detail": null }
```

`status` is `degraded` when the models are not loaded or the database does not
answer; `detail` then says why. History and statistics keep working without
the models; only the analyze endpoints return `503`.

## GET /model-info

The contents of `models/evaluation_report.json`, written by
`python -m training.evaluate`. `404` until that script has been run.

```json
{
  "report": {
    "generated_at": "...",
    "dataset": "SemEval-2014 Task 4, gold test set",
    "domains": ["laptops", "restaurants"],
    "training": {
      "aspect": { "...": "..." },
      "sentiment": { "...": "..." },
      "overall": { "...": "..." }
    },
    "results": {
      "all": {
        "test_sentences": 1600,
        "aspect_extraction": { "...": "..." },
        "aspect_sentiment": { "...": "..." },
        "aspect_sentiment_by_sentence_type": { "uniform": { "...": "..." }, "mixed": { "...": "..." } },
        "overall_sentiment": { "...": "..." },
        "end_to_end": { "...": "..." }
      },
      "laptops": { "...": "..." },
      "restaurants": { "...": "..." }
    }
  }
}
```

`training` holds each deployed model's `training_log.json` (hyperparameters,
validation score per epoch, training time), so the response identifies exactly
which models the numbers belong to. `results` has one entry for all test data
and one per domain.

The same numbers, as tables, are in [results.md](results.md). `report` is
typed loosely on purpose: the evaluation script owns its layout.
