# Training and evaluation

Run everything from the `backend` directory with the virtual environment active.

```
python -m training.prepare_dataset                 # 1. download + validate + split   (< 1 min)
python -m training.train_aspect                    # 2. aspect extraction model  -> models/aspect_extraction
python -m training.train_sentiment --task aspect   # 3. aspect sentiment model   -> models/sentiment
python -m training.train_sentiment --task overall  # 4. overall sentiment model  -> models/overall_sentiment
python -m training.evaluate                        # 5. test-set metrics         -> docs/results.md
```

## Retraining safely: `run_all` and `promote`

The five commands above write straight into the folders the application loads.
To retrain without touching the deployed models, use the chain instead:

```
python -m training.run_all --smoke    # 1. whole chain on 32 sentences (minutes): does it run?
python -m training.run_all            # 2. train all three models, evaluate new and deployed ones
python -m training.run_all --status   #    (from a second terminal) done / running / pending
python -m training.promote            # 3. compare new with deployed on both test domains
python -m training.promote --apply    # 4. install the candidates that qualify
python -m training.evaluate           # 5. rewrite docs/results.md for the installed models
```

- `run_all` trains into `models/candidates/` with the default options below,
  one model after another, and writes each step's output to
  `models/candidates/logs/<step>.log`.
- **It can be interrupted.** A step is complete once its last file exists
  (`training_log.json` for a model, `evaluation_report.json` for an
  evaluation). Starting `run_all` again skips complete steps; a training step
  that was interrupted starts over. If the process was killed, delete
  `models/candidates/logs/run_all.lock` first.
- It keeps Windows and the display awake while it runs. Closing the laptop lid
  still suspends the machine, and a suspended machine does not train: keep it
  plugged in with the lid open.
- `promote` decides per model with one metric, on the laptops and restaurants
  test sets: span F1 for aspect extraction, macro-F1 for both sentiment
  models. A candidate qualifies when that metric is higher on both domains
  together and at most 0.01 lower on either one. Otherwise it reports
  "needs decision" and installs nothing for that model.
- Nothing is deleted: the replaced model moves to `models/previous/`, and the
  candidate folder is copied, not moved.
- Delete `models/candidates/_smoke/` after a smoke test.

Always finish with `python -m training.evaluate`: `pytest` fails if
`models/evaluation_report.json` does not describe the installed models.

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
