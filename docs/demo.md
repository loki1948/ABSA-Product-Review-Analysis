# Demo script

A run-through of the whole application in about five minutes. It needs the
three trained models in `models/` (see the README, "Train the models").

## Before the audience arrives

Terminal 1:

```powershell
cd backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app
```

Wait for "Models loaded." (about 20 seconds). Terminal 2:

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. The header must show a green dot and "Backend
connected". Keep the laptop plugged in: model inference on battery is slower.

To start from an empty history, stop the backend, delete `data/absa.db` and
start it again.

## The demo

| Step | Do | Point out |
|---|---|---|
| 1. The idea | Home page | One label hides what the aspect view shows. The example on this page is a fixed illustration |
| 2. One review | Analyzer, click "Laptop review", Analyze | The overall label on the left; on the right each aspect is highlighted in the text and listed with its sentiment and confidence |
| 3. Another domain | Click "Restaurant review", Analyze | The same models handle restaurant reviews: they were trained on both domains |
| 4. Your own review | Ask the audience for a sentence, type it | No aspect list is built in; the model decides what an aspect is |
| 5. No aspects | Type "It arrived on Tuesday." | The system says that no aspect was found instead of inventing one |
| 6. Many reviews | Batch page, upload `data/samples/demo_reviews.csv`, Analyze | Progress in chunks of ten; download the results as CSV |
| 7. History | History page, filter "Negative", open one row, delete one | Everything analysed is stored; the full analysis can be reopened |
| 8. Aggregates | Dashboard | Which aspects customers mention most and how they feel about each: the view a seller would use |
| 9. How good is it | Dashboard, "Model performance" | Test-set scores per domain, read from the evaluation report; details in `docs/results.md` |
| 10. Honest limits | `docs/error_analysis.md` | The neutral class and sentences that mix sentiments are the hard cases |

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Red dot, "Cannot reach the backend" | Backend not running | Start terminal 1 |
| Amber dot, "No trained model in ..." | A model folder is missing | Copy or train the models, restart the backend |
| First analysis takes several seconds | Models warming up | Analyse one review before the demo |
| Port 8000 or 5173 in use | An old process | Close the other terminal, or `uvicorn app.main:app --port 8001` and set the proxy target in `frontend/vite.config.ts` |
