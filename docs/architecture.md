# Architecture

## The idea in one paragraph

Traditional sentiment analysis gives a whole review one label. This system
first finds the individual product aspects mentioned in a review (aspect
extraction), then decides the sentiment towards each of them (aspect sentiment
classification), and also reports the traditional overall sentiment so the two
can be compared side by side.

## System overview

```
 Browser (React + TypeScript + Tailwind + Recharts)        frontend/
    |   src/services/api.ts  <- the only place that talks HTTP
    |
    |   JSON over HTTP, all routes under /api
    v
 FastAPI application                                       backend/app/main.py
    |-- api/routes/analysis.py   POST /api/analyze
    |-- api/routes/reviews.py    GET  /api/reviews, /api/reviews/{id}, /api/statistics
    |                            DELETE /api/reviews/{id}
    |-- api/routes/health.py     GET  /api/health, /api/model-info
    |
    |-- nlp/pipeline.py          ABSAPipeline.analyze(review)
    |      |-- nlp/preprocessing.py       clean, split sentences, tokenise, BIO, context
    |      |-- nlp/aspect_extraction.py   BIO tags -> aspect terms + offsets + context
    |      |      '-- models/aspect_model.py     BERT token classifier     -> models/aspect_extraction/
    |      '-- nlp/sentiment.py           aspect sentiment + overall sentiment
    |             '-- models/sentiment_model.py  BERT sequence classifier  -> models/sentiment/
    |                                            (same class, 2nd model)   -> models/overall_sentiment/
    |
    '-- database/ (SQLAlchemy)   reviews 1 --- * aspect_sentiments        -> data/absa.db (SQLite)

 Offline (run once, or whenever the models are retrained)   backend/training/
    prepare_dataset.py -> train_aspect.py -> train_sentiment.py (x2: aspect, overall) -> evaluate.py
```

## What happens on `POST /api/analyze`

Input: `"Great camera, but the battery life is terrible."`

| Step | Code | Result for the example |
|---|---|---|
| 1. Validate request | `schemas/analysis.py` | non-blank, at most 5000 characters |
| 2. Clean | `preprocessing.clean_text` | Unicode/HTML/whitespace normalised; words untouched |
| 3. Split sentences | `preprocessing.split_sentences` | 1 sentence |
| 4. Tokenise with offsets | `preprocessing.tokenize` | `Great` `camera` `,` `but` `the` `battery` `life` ... |
| 5. Tag tokens | `AspectExtractor.predict` | `O B-ASPECT O O O B-ASPECT I-ASPECT O O O` |
| 6. Tags to aspects | `aspect_extraction.extract_aspects` | `camera` (6-12), `battery life` (22-34) |
| 7. Context | `preprocessing.extract_context` | "Great camera" / "the battery life is terrible" |
| 8. Aspect sentiment | `sentiment.classify_aspects` | aspect-sentiment model: one `[CLS] sentence [SEP] aspect [SEP]` input per aspect |
| 9. Overall sentiment | `sentiment.classify_overall` | overall-sentiment model: `[CLS] sentence [SEP]` per sentence, probabilities averaged |
| 10. Store | `database/crud.create_review` | 1 row in `reviews`, 2 rows in `aspect_sentiments` |
| 11. Respond | `api/deps.review_to_response` | JSON described in [API.md](API.md) |

(The tags and sentiments in this table illustrate the data flow. Measured model
quality is in [results.md](results.md).)

## Why a two-stage pipeline

- **Stage 1, token classification.** Deciding *which words are aspects* is a
  per-word decision, so the model outputs one label per word (BIO scheme).
- **Stage 2, sequence classification.** Deciding *the sentiment towards one
  aspect* is one decision per (sentence, aspect) pair, so the model outputs one
  label per input pair.

Each stage can be trained, evaluated, debugged and improved on its own, and each
has standard metrics. The cost is error propagation: an aspect that stage 1
misses never reaches stage 2. `training/evaluate.py` therefore also measures the
end-to-end result.

A third model, the overall-sentiment classifier, is not part of ABSA. It is the
"existing system" (one label per review) that the project improves on, kept so
both can be shown side by side. It is a separate model because training one
classifier for both jobs made it less aspect-specific (see
[methodology.md](methodology.md), section 4.3).

## Database

```
reviews                              aspect_sentiments
-------                              -----------------
id                 PK                id                 PK
review_text                          review_id          FK -> reviews.id (cascade delete)
overall_sentiment                    aspect             as written in the review
overall_confidence                   aspect_normalized  lowercase + lemmatised, for grouping
created_at         (UTC)             sentiment
                                     confidence
                                     context
                                     start_char, end_char   offsets into review_text
```

One review has many aspects, hence two tables. `aspect_normalized` exists so
that the statistics count "Batteries" and "battery" as the same aspect while the
original wording is kept for display. SQLite is used through SQLAlchemy, so
moving to PostgreSQL later only means changing `ABSA_DATABASE_URL`.

## Design decisions worth knowing

| Decision | Reason |
|---|---|
| Training and inference share `nlp/preprocessing.py` and the model wrappers in `models/` | The model must see text prepared the same way at inference as during training. Evaluation also uses these wrappers, so reported metrics describe the deployed code path. |
| No stop-word removal, stemming or punctuation stripping | BERT relies on context; removing "not" or "but" changes the meaning. |
| Aspects are returned with character offsets | The frontend can highlight them in the review text. |
| Models are loaded once at startup (`lifespan`) | Loading takes seconds; a request should only pay for inference. The three models need roughly 1.5 GB of RAM. |
| If the models are missing the API still starts | History and statistics keep working, `/api/health` reports `degraded` with the reason, `/api/analyze` returns 503. Frontend work does not require trained models. |
| Routes are plain `def`, not `async def` | FastAPI runs them in a thread pool, so CPU-heavy inference does not block the event loop. |
| No hard-coded aspect list anywhere | What counts as an aspect is learnt from annotated data. |
| Padding to the longest sequence in each batch | Review sentences are short; this makes CPU training and inference practical. |

## Configuration

Environment variables with the prefix `ABSA_`, or a `backend/.env` file. See
`backend/.env.example` and `backend/app/config.py`. No secrets are needed.
