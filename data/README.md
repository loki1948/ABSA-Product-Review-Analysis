# Data

Nothing in `raw/` or `processed/` is committed to git. Recreate it with:

```
cd backend
python -m training.prepare_dataset
```

## Source

SemEval-2014 Task 4, *Aspect Based Sentiment Analysis* (Pontiki et al., 2014):
laptop and restaurant review sentences annotated with aspect terms and their
polarity. The script downloads the four original XML files (two training files,
two gold test files) into `raw/`. The dataset is distributed for research use;
cite the paper in the project report.

## Files written to `processed/`

| File | Content |
|---|---|
| `train.jsonl`, `val.jsonl`, `test.jsonl` | One sentence per line (format below) |
| `sentiment_train.csv`, `sentiment_val.csv`, `sentiment_test.csv` | One row per aspect: `id, domain, review, aspect, from, to, sentiment` |
| `dataset_stats.json` | Sentence, aspect and polarity counts per split and domain, plus what validation removed |

One line of a `.jsonl` file:

```json
{
  "id": "laptops:2791",
  "domain": "laptops",
  "text": "Most everything is fine with this machine: speed, capacity, build.",
  "aspects": [
    {"term": "speed", "from": 43, "to": 48, "polarity": "positive"},
    {"term": "capacity", "from": 50, "to": 58, "polarity": "positive"},
    {"term": "build", "from": 60, "to": 65, "polarity": "positive"}
  ],
  "tokens": ["Most", "everything", "is", "fine", "with", "this", "machine", ":", "speed", ",", "capacity", ",", "build", "."],
  "tags": ["O", "O", "O", "O", "O", "O", "O", "O", "B-ASPECT", "O", "B-ASPECT", "O", "B-ASPECT", "O"]
}
```

`from`/`to` are character offsets into `text`. `tokens` and `tags` have the same
length and are the input and target of the aspect-extraction model.

## Other files

`absa.db` is the application's SQLite database (review history). It is created
when the API starts and is not committed.
