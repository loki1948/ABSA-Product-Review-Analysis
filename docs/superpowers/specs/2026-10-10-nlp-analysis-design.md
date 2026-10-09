# Sub-project 3: NLP analysis — design

Date: 2026-10-10. Part 3 of 4, see
[../../PROJECT_CHECKLIST.md](../../PROJECT_CHECKLIST.md).

## 1. Goal

Evidence for the report: how much the BERT models add over a method without
them, where they still fail, and how well they transfer to reviews unlike their
training data. Everything is produced by scripts or notebooks that can be
re-run; no number is typed by hand.

## 2. Deliverables

### 2.1 Non-BERT baseline (`backend/training/baseline.py`)

A rule-and-lexicon system scored with the same metric functions and the same
test data as the BERT models.

- **Aspect extraction:** part-of-speech tag each sentence (NLTK averaged
  perceptron tagger) and take every maximal run of nouns (`NN`, `NNS`) as one
  aspect. A two-noun run such as "battery life" becomes one aspect.
- **Aspect sentiment:** count opinion words from the Hu and Liu (2004) opinion
  lexicon (`nltk.corpus.opinion_lexicon`) inside the aspect's clause, as found
  by the existing `extract_context`. A negation word (`not`, `n't`, `no`,
  `never`, `without`, `hardly`) among the three tokens before an opinion word
  flips it. Positive total gives positive, negative gives negative, zero gives
  neutral.
- **Overall sentiment:** the same count over the whole sentence.
- **Output:** `models/baseline_report.json` in the layout of the BERT report
  (scopes `all`, `laptops`, `restaurants`), and `docs/baseline.md` with one
  table per scope placing baseline and BERT side by side and the difference.
  The BERT column is read from `models/evaluation_report.json`.

The baseline lives in `training/`, not in `app/`: the application's pipeline
keeps its rule that both stages are learnt models.

### 2.2 Error analysis (`backend/training/error_analysis.py`, notebook 03)

From the deployed models on the test set, written to `docs/error_analysis.md`:

- aspect extraction errors by type: missed entirely, boundary error (overlaps a
  gold span without matching it), spurious; the 15 most often missed aspect
  terms per domain; recall for one-word versus multi-word aspects;
- sentiment errors: the confusion matrix read as sentences, the share of each
  confusion pair, accuracy for uniform versus mixed sentences, and accuracy by
  confidence band (below 0.6, 0.6 to 0.8, above 0.8), which shows whether the
  confidence shown in the interface means anything;
- twenty sampled misclassified examples with sentence, aspect, gold and
  predicted label (fixed seed).

### 2.3 Cross-domain transfer (`docs/transfer.md`)

Built by `error_analysis.py` from reports that already exist:

- the laptops-only models (now in `models/previous/`) evaluated on restaurant
  reviews, from `models/candidates/eval/current/evaluation_report.json`,
  against the two-domain models on the same reviews. This is a measured
  transfer result.
- a qualitative check on a third category with no labelled data: twelve
  hand-written reviews (phones, hotels, headphones) in
  `data/samples/other_domains.csv`, run through the pipeline, with the output
  listed for a reader to judge. It is stated as an illustration, not a metric;
  no correctness figure is claimed for it.

### 2.4 Notebooks (`notebooks/`)

- `01_data_exploration.ipynb`: split sizes, polarity distribution per domain,
  sentence and aspect length, most frequent aspect terms, the leakage check.
- `02_preprocessing.ipynb`: one sentence followed through cleaning,
  tokenisation, BIO tagging and word-piece alignment.
- `03_model_evaluation.ipynb`: the results tables, both confusion matrices, the
  baseline comparison and the error analysis, by calling the scripts above.

Notebooks call functions from `app/` and `training/`; they contain no logic of
their own. Each must execute top to bottom with
`jupyter nbconvert --execute`. `jupyter` and `nbconvert` go into a new
`backend/requirements-dev.txt`.

## 3. Testing

| Unit | Cases |
|---|---|
| noun-run extraction | single noun, two-noun compound, two separate aspects, no nouns |
| lexicon sentiment | positive, negative, no opinion word gives neutral, negation flips, negation further than three tokens does not |
| baseline report | has the three scopes and the sections `promote` and the frontend read |
| error categories | missed, boundary, spurious counted correctly on a hand-made example |
| confidence bands | band edges assigned correctly |
| notebooks | each executes without error |

## 4. Out of scope

Training a non-BERT machine-learning baseline (CRF, SVM), statistical
significance tests, and collecting or annotating a new dataset.
