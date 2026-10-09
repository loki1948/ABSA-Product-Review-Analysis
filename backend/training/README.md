# Training and evaluation

Run everything from the `backend` directory with the virtual environment active.

```
python -m training.prepare_dataset                 # 1. download + validate + split   (< 1 min)
python -m training.train_aspect                    # 2. aspect extraction model  -> models/aspect_extraction
python -m training.train_sentiment --task aspect   # 3. aspect sentiment model   -> models/sentiment
python -m training.train_sentiment --task overall  # 4. overall sentiment model  -> models/overall_sentiment
python -m training.evaluate                        # 5. test-set metrics         -> docs/results.md
```

## Options

Both training scripts accept (the exact settings of the shipped models are in
`docs/results.md`):

| Option | Default | Meaning |
|---|---|---|
| `--domains` | `laptops restaurants` | Which review domains to train on |
| `--epochs` | `3` (aspect extraction), `4` (sentiment) | Passes over the training data |
| `--batch-size` | `16` | |
| `--lr` | `3e-5` (aspect), `2e-5` (sentiment) | Peak learning rate |
| `--max-length` | `128` | Maximum word-pieces per input |
| `--seed` | `42` | |
| `--model-name` | `bert-base-uncased` | Pretrained checkpoint to fine-tune |
| `--limit N` | off | Use only N sentences: a quick check that the script runs |
| `--output-dir` | `models/...` | Where the best checkpoint is saved |

`train_sentiment` needs `--task aspect` (sentence + aspect pairs) or
`--task overall` (whole sentences, weak labels); they are two separate models.
`evaluate` tests on the domains the aspect-extraction model was trained on
unless `--domains` is given.

## How long it takes

On a 4-core laptop CPU one training step (16 examples) takes about 3 to 5
seconds. The time each shipped model took is recorded in its
`training_log.json` and shown in `docs/results.md`.

On a GPU the same runs take a few minutes. With free Google Colab: upload the
`backend` folder, select a GPU runtime, `pip install -r requirements.txt`, run
the five commands above, then download the three folders under `models/`. The
scripts use the GPU automatically when one is available.

## What gets written

- `models/<name>/` : model weights, tokenizer, and `training_log.json`
  (hyperparameters, loss and validation score per epoch, training time).
- `models/evaluation_report.json` : every test metric, machine-readable. Served
  by `GET /api/model-info`.
- `docs/results.md`, `docs/figures/sentiment_confusion_matrix.png` : the same
  metrics as tables and a figure for the report.
