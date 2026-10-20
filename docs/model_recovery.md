# Model integrity and recovery

What is on disk, how to check it, and how to get a working set of models back.
Nothing here is in git: model folders are too large (see
[model_sharing.md](model_sharing.md) for passing them to teammates).

## What exists (checked 2026-10-10)

| Folder under `models/` | Content | Size | Needed to run the app |
|---|---|---|---|
| `aspect_extraction`, `sentiment`, `overall_sentiment` | The deployed models, trained on both domains | 1.22 GB | Yes |
| `candidates/aspect_extraction`, `candidates/sentiment`, `candidates/overall_sentiment` | The same three models as `run_all` wrote them, before promotion | 1.22 GB | No: byte-identical copies of the deployed models |
| `candidates/eval`, `candidates/logs` | Evaluation reports and training logs of that run | under 1 MB | No, but they are the record of the run |
| `previous/aspect_extraction-20261010-093116` | The earlier aspect model, laptops only (has its training log) | 0.41 GB | No |
| `previous/sentiment-20261010-093116` | The earlier sentiment model: a checkpoint from an interrupted run, no training log | 0.41 GB | No |
| `sentiment_joint_backup` | The first, joint sentiment model with its own evaluation report | 0.41 GB | No |
| `train_sentiment_aspect.log` | Log of a retrain that died on 2026-10-08 | 1 KB | No |

Tracked in git and sufficient to reproduce every published number's source:
`models/evaluation_report.json`, `models/baseline_report.json`,
`models/laptops_only_report.json`.

## Check the deployed models

```powershell
cd backend
python -m pytest -m model        # 10 tests: models load, analyse, and match the published report
```

`test_report_describes_the_deployed_models` fails if any of the three folders
is not the model the committed evaluation report was computed from.

To compare the deployed weights with a copy, file by file:

```powershell
foreach ($m in "aspect_extraction","sentiment","overall_sentiment") {
  (Get-FileHash models\$m\model.safetensors).Hash -eq (Get-FileHash models\candidates\$m\model.safetensors).Hash
}
```

Three times `True` means the copy is intact. This was the result on 2026-10-10
for the weights, config, tokenizer and training log of all three models.

## Recover

| Situation | Do this |
|---|---|
| A deployed folder is incomplete or was deleted | Stop the backend, then `python -m training.promote --apply`: a model reported as "already installed" is copied again from `models/candidates` when a file is missing or has a different size. A file damaged without a change in size is not noticed: compare hashes as shown above. A folder whose `training_log.json` is missing cannot be identified and is reported as "needs decision", not repaired: restore it with `scripts/package_models.ps1 -Install` (into an empty folder) or move it away and run `promote --apply` again. If the backend still holds a model open, that model is left as it is, the others are installed, and the command exits with code 4 |
| `models/candidates` is gone too | Move the three deployed folders away, then unpack the archive: `.\scripts\package_models.ps1 -Install absa-models.zip` (the hash is checked first; it refuses to unpack over a folder that is not empty) |
| No archive either | Retrain: `python -m training.run_all`, then `promote --apply`, then `evaluate`. Several hours on a CPU. The numbers can differ slightly from the committed report, which `evaluate` then rewrites |
| You want the previous models back | Move the deployed folder away, then move the folder from `models/previous` into its place and rename it (drop the date suffix). Run `python -m training.evaluate` afterwards, or `pytest -m model` fails by design. `promote` will then answer "needs decision" for that model until `python -m training.run_all` has evaluated it |

Never mix folders from different runs without re-running
`python -m training.evaluate`.

## What can be removed, and what it frees

Only after an archive exists outside this machine (shared drive, USB disk):

| Remove | Frees | What is lost |
|---|---|---|
| `models/candidates/aspect_extraction`, `candidates/sentiment`, `candidates/overall_sentiment` | 1.22 GB | The local second copy. Keep `candidates/eval` and `candidates/logs` |
| `models/previous/*` | 0.81 GB | The earlier models. Their test scores stay in `models/laptops_only_report.json`; the models themselves could not be recreated exactly (the sentiment one has no training record) |
| `models/sentiment_joint_backup` | 0.41 GB | The first joint model and its evaluation report (`evaluation_report_joint.json`, not tracked in git: copy it out first if wanted) |
| `models/train_sentiment_aspect.log` | 1 KB | Nothing of value |

Total: about 2.44 GB. Without the three `candidates` model folders the only
copies of the deployed models are the deployed folders and the archive.
