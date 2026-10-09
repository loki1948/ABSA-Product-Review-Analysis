# Sharing the trained models

The three models are about 420 MB each and are not stored in git. Everyone
needs the same three folders to run the application:

```
models/aspect_extraction/
models/sentiment/
models/overall_sentiment/
```

`models/evaluation_report.json` is in git and describes exactly these models.

## Option 1: a shared drive (simplest)

The person who trained the models, from the project folder:

```powershell
Compress-Archive -Path models\aspect_extraction, models\sentiment, models\overall_sentiment -DestinationPath absa-models.zip
Get-FileHash absa-models.zip -Algorithm SHA256
```

Upload `absa-models.zip` (about 1.2 GB) to the team's shared drive and post the
hash in the team chat. Everyone else downloads it and runs, from the project
folder:

```powershell
Get-FileHash absa-models.zip -Algorithm SHA256      # must equal the posted hash
Expand-Archive absa-models.zip -DestinationPath models -Force
```

## Option 2: train them yourself

`python -m training.run_all` (see `backend/training/README.md`). Several hours
on a laptop CPU, minutes on a GPU. Because of random initialisation on
different hardware, your numbers can differ slightly from `docs/results.md`;
run `python -m training.evaluate` afterwards so the report matches your models.

## Check that you have the right models

```powershell
cd backend
pytest -m model
```

All tests must pass and none may be skipped. `test_report_describes_the_deployed_models`
fails if your model folders are not the ones the committed evaluation report
was computed from.

## Do not

- commit model folders to git (`.gitignore` excludes them);
- mix models from different training runs: the three folders and the
  evaluation report belong together.
