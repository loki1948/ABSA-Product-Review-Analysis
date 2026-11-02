# Demo talk: what to say

The speaker notes that go with [demo.md](demo.md). `demo.md` lists the clicks;
this file gives the explanation for each part. All figures come from
[results.md](results.md) and [baseline.md](baseline.md). The talk takes about
10 to 12 minutes.

---

## 1. The problem (1 min)

> "Normal sentiment analysis gives a whole review one label. Take this review:
> *'The screen is gorgeous and the keyboard feels great, but the battery life is
> terrible.'* A normal model calls it positive or mixed, and a seller learns
> nothing. Our system says **screen: positive, keyboard: positive, battery life:
> negative**. That is **Aspect-Based Sentiment Analysis (ABSA)**."

The point to get across: one label hides what the customer actually said about
each feature.

---

## 2. The working process (2 min)

Draw or show this flow:

```
Review text
   │
   ▼
1. Preprocessing      clean text → split into sentences → split into words (with positions)
   │
   ▼
2. Model 1: Aspect extraction      "which words are product features?"
   │      → screen, keyboard, battery life
   ▼
3. Model 2: Aspect sentiment       "how does the writer feel about THIS feature?"
   │      → asked once per aspect: (sentence, "screen") → positive
   │                                (sentence, "battery life") → negative
   ▼
4. Model 3: Overall sentiment      "what is the overall tone?" (for comparison)
   │
   ▼
5. Save to database → show in Analyzer, Batch, History, Dashboard
```

The stack: **FastAPI** backend (Python, PyTorch, Hugging Face Transformers),
**React** frontend, **SQLite** database.

### Preprocessing
- Cleans HTML, odd characters and extra spaces.
- Splits the review into sentences, because the models were trained on single
  sentences.
- **No stop-word removal or stemming.** "not good" must not become "good". BERT
  reads the whole context, so it needs the original words.

---

## 3. The three models: what each does and why it is there (3 min)

All three start from **BERT (`bert-base-uncased`)**, a model pretrained on a large
amount of English text. We **fine-tuned** each one on our task.

### Model 1: Aspect extraction (finds the features)
- **What it does:** labels every word as the start of an aspect (`B`), the inside
  of an aspect (`I`), or not an aspect (`O`):
  ```
  The  battery  life  is  great  but  the  screen  is  dim
  O    B        I     O   O      O    O    B       O   O
  ```
- **Why it is needed:** there is no fixed list of features. The model learns from
  context what counts as a feature, including multi-word ones like "battery life".
- **Score:** **F1 0.85** on the test set (an aspect counts only when its
  boundaries match the human annotation exactly).

### Model 2: Aspect sentiment (judges each feature)
- **What it does:** takes the sentence **plus one aspect** as input:
  `[CLS] sentence [SEP] battery life [SEP]` → positive / negative / neutral.
- **Why the aspect is in the input:** the same sentence can then get a different
  answer for each aspect. That is what makes the analysis aspect-based.
- **Score:** **81.5% accuracy**, macro-F1 0.75.

### Model 3: Overall sentiment (the traditional view)
- **What it does:** one label for the whole sentence, which is ordinary
  sentiment analysis.
- **Why we kept it:** to show *traditional vs. aspect-based* next to each other in
  the app, which is the whole argument of the project.
- **Why it is a separate model:** a model trained to judge the whole sentence
  learns to *ignore* which aspect it was asked about. That is the opposite of
  what Model 2 must do, so we gave the two tasks separate models.

### Why BERT and not a simple rule-based system?
We built a rule-based baseline (nouns = aspects, a dictionary of opinion words
= sentiment) and scored both systems on the same test sentences:

| | Rule-based baseline | Our BERT models |
|---|---|---|
| Aspect extraction F1 | 0.38 | **0.85** |
| Aspect sentiment accuracy | 66% | **82%** |
| End-to-end F1 (aspect and sentiment both right) | 0.25 | **0.70** |

> "Rules can't tell that 'runs hot' is negative for a laptop or that 'long wait'
> is negative for a restaurant. BERT learns that from examples."

---

## 4. Data and training (1 min)

- **Dataset:** SemEval-2014 Task 4, the standard ABSA benchmark. Human-labelled
  review sentences from **laptops** and **restaurants**: about 5,400 training
  sentences, and 1,600 test sentences that are never used in training.
- **Data checks:** we found and removed 2 training sentences that also appear in
  the test set, plus 29 duplicates, so the test scores are not inflated.
- **Training:** on a CPU only, about 3.5 hours for all three models. The best
  epoch was chosen on a validation split.

---

## 5. Live demo (4 min). Follow the steps in [demo.md](demo.md)

| Step | Say |
|---|---|
| Analyzer, "Laptop review" | "Left: the one traditional label. Right: each aspect highlighted in the text with its own sentiment and confidence." |
| "Restaurant review" | "Same models, different domain. They were trained on both." |
| An audience sentence | "No feature list is built in. The model decides what an aspect is." |
| "It arrived on Tuesday." | "No aspect here, and the system says so instead of inventing one." |
| Batch, upload `data/samples/demo_reviews.csv` | "This is how a business would use it: hundreds of reviews at once, results downloadable as CSV." |
| History | "Every analysis is stored and can be reopened or filtered." |
| Dashboard | "This is the seller's view: which features customers talk about most and how they feel about each." |
| Dashboard, "Model performance" | "These scores come from the evaluation report on the test set, not from numbers typed in by hand." |

---

## 5a. Page by page: what each page does and which models it uses

The three models are loaded **once**, when the backend starts. They run **only
when a review is analysed**, which happens on the Analyzer and Batch pages. The
other pages show results the models already produced.

| Page | Models that run on this page | Data source |
|---|---|---|
| Home | none | a fixed example written into the page |
| Analyzer | all three | `POST /api/analyze` |
| Batch | all three, once for every review | `POST /api/analyze/batch`, 10 reviews per request |
| History | none; shows earlier model results | `GET /api/reviews` (database) |
| Dashboard | none; counts earlier model results | `GET /api/statistics`, `GET /api/model-info` |

The header dot on every page calls `GET /api/health`, which reports whether the
models are loaded and the database answers.

### Home (`/`)
- **Purpose:** introduces the problem: one label vs. a label for each aspect.
- **What is on it:** the "One review, two views" example and a three-step "How it
  works" panel (find aspects, judge each aspect, overall label).
- **Models:** none. The example is a fixed illustration and is not computed live.
  Say so if asked.

### Analyzer (`/analyze`)
- **Purpose:** analyse one review and see the result straight away.
- **Process when you click Analyze:**
  1. Preprocessing cleans the text and splits it into sentences (NLTK).
  2. **Model 1, Aspect extraction** (BERT token classifier) tags each word
     B/I/O and returns the aspects with their positions in the text, which is how
     they are highlighted.
  3. **Model 2, Aspect sentiment** (BERT sentence-pair classifier) is called once
     per aspect with (sentence, aspect) and returns positive/negative/neutral
     plus a confidence.
  4. **Model 3, Overall sentiment** (BERT single-sentence classifier) gives the
     whole review one label. For several sentences, the probabilities are
     averaged.
  5. If "save" is ticked, the result is stored in SQLite.
- **On screen:** left, the overall label from Model 3 (the traditional view).
  Right, the highlighted text, the aspect table and the chart from Models 1 and 2
  (the aspect-based view).
- **Why all three:** Models 1 and 2 together *are* ABSA. Model 3 is there so the
  traditional result can be compared side by side.

### Batch (`/batch`)
- **Purpose:** analyse many reviews at once, the way a business would.
- **Input:** a CSV upload (the `review` or `text` column, otherwise the first
  column), a .txt file, or pasted text. "Read the text as" switches between *one
  review per line* and *CSV*.
- **Process:** the browser sends 10 reviews at a time to `/api/analyze/batch`.
  On the server, **each review goes through the same three-model pipeline** as on
  the Analyzer. The progress bar moves after each group of 10, and Stop or
  leaving the page halts the run.
- **Output:** a results table and a CSV download, protected against spreadsheet
  formula injection. Results are saved to History if "Save to history" is ticked.
- **Models:** all three, once for every review.

### History (`/history`)
- **Purpose:** every review saved from the Analyzer or Batch page.
- **Features:** filter by overall sentiment (positive/negative/neutral), page
  through results, reopen the full analysis, delete a review.
- **Models:** none run here. The labels shown are what Models 1–3 produced when
  the review was analysed, read back from the database.

### Dashboard (`/dashboard`)
- **Purpose:** the seller's summary over all saved reviews.
- **Charts:**
  - *Overall sentiment distribution*: counts of Model 3's labels.
  - *Most frequent aspects*: the aspects Model 1 found most often. Aspects are
    grouped with WordNet lemmatisation, so "battery" and "batteries" count
    together. That step is a dictionary lookup, not a trained model.
  - *Sentiment for each aspect*: how often each aspect was judged positive,
    negative or neutral by Model 2.
- **"Model performance":** test-set scores (F1, accuracy, macro-F1 per domain),
  read from `models/evaluation_report.json`, which `training/evaluate.py`
  produced. No model runs when this panel loads, and none of the numbers are
  typed in by hand.
- **Models:** none run here. The page aggregates earlier results and reports how
  well the models scored.

---

## 6. Honest limits (1 min)

Say these before someone asks:
- **Neutral is the hardest class** (F1 0.58). Neutral is often mistaken for
  negative.
- **Sentences with mixed feelings are harder:** 66% accuracy when the aspects
  differ, against 85% when they all agree.
- **Only explicit aspects:** "It dies after two hours" implies *battery*, but the
  word never appears, so it is not found.
- **Trained on 2014 laptop and restaurant reviews.** Other products work only as
  far as the model generalises.

---

## Likely questions

| Question | Answer |
|---|---|
| Why not ChatGPT or another LLM? | It runs locally and offline on a CPU, the results can be repeated, it is measured on a standard benchmark, and it costs nothing per review. |
| What is F1? | The balance of precision (how many of the found aspects are right) and recall (how many of the real aspects were found). |
| Why macro-F1 and not just accuracy? | Most aspects are positive. Accuracy alone would hide weak neutral performance. |
| Why BERT uncased? | A strong pretrained model that is small enough to fine-tune on a CPU. Letter case adds little for reviews. |
| How fast is it? | The models load once at startup, in about 20 seconds. After that, a single review is analysed in a moment on a CPU. Time one before the demo so you can give a real figure. |
| Does it work on other products? | Partly. See `data/samples/other_domains.csv` and [transfer.md](transfer.md). |
