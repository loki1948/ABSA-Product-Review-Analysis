"""Writes the three notebooks from the cell lists below.

    python notebooks/build_notebooks.py

The notebooks are generated so that their code stays reviewable as plain
Python in one place. They contain no logic of their own: every cell calls
functions from ``backend/app`` or ``backend/training``.

Execute them (this also checks that they still run):

    jupyter nbconvert --to notebook --execute --inplace notebooks/01_data_exploration.ipynb
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

HERE = Path(__file__).resolve().parent

SETUP = """\
import sys
from pathlib import Path

# Make `app` and `training` importable from the notebooks folder.
BACKEND = Path.cwd().resolve().parent / "backend" if Path.cwd().name == "notebooks" else Path.cwd() / "backend"
sys.path.insert(0, str(BACKEND))

import pandas as pd
import matplotlib.pyplot as plt

pd.set_option("display.max_colwidth", 120)"""

NOTEBOOKS: dict[str, list[tuple[str, str]]] = {
    "01_data_exploration.ipynb": [
        ("md", "# 1. Data exploration\n\nSemEval-2014 Task 4 (laptops and restaurants) after `python -m training.prepare_dataset`.\nEvery number is computed from `data/processed`."),
        ("code", SETUP),
        ("code", """\
from training.common import load_split

splits = {name: load_split(name) for name in ("train", "val", "test")}
sentences = pd.DataFrame(
    {"split": name, "domain": r["domain"], "tokens": len(r["tokens"]), "aspects": len(r["aspects"])}
    for name, records in splits.items() for r in records
)
sentences.groupby(["split", "domain"]).agg(
    sentences=("tokens", "size"),
    with_aspects=("aspects", lambda s: int((s > 0).sum())),
    aspect_terms=("aspects", "sum"),
    mean_tokens=("tokens", "mean"),
).round(2)"""),
        ("md", "## Polarity of the aspect terms\n\nPositive is the largest class and neutral the smallest, which is why macro-F1 is reported next to accuracy. `conflict` terms are used for aspect extraction but left out of sentiment classification."),
        ("code", """\
aspects = pd.DataFrame(
    {"split": name, "domain": r["domain"], "term": a["term"].lower(),
     "words": len(a["term"].split()), "polarity": a["polarity"]}
    for name, records in splits.items() for r in records for a in r["aspects"]
)
polarity = aspects[aspects.split == "train"].groupby(["domain", "polarity"]).size().unstack(fill_value=0)
display(polarity)
polarity.plot(kind="bar", figsize=(7, 3.5), rot=0, title="Aspect polarity in the training split")
plt.ylabel("aspect terms"); plt.tight_layout(); plt.show()"""),
        ("md", "## How many aspects does a sentence have?\n\nMany sentences have none: the extraction model must also learn to stay silent."),
        ("code", """\
train = sentences[sentences.split == "train"]
display(train.groupby("domain")["aspects"].value_counts().unstack(fill_value=0).iloc[:, :6])
print("share of training sentences without any aspect:")
print((train.aspects == 0).groupby(train.domain).mean().round(3))"""),
        ("md", "## Sentences that mix sentiments\n\nOnly in these does a model have to be aspect-specific to be right. They are a minority, which is why they are evaluated separately in `docs/results.md`."),
        ("code", """\
def mixed(record):
    polarities = {a["polarity"] for a in record["aspects"] if a["polarity"] != "conflict"}
    return len(polarities) > 1

rows = []
for name, records in splits.items():
    with_aspects = [r for r in records if r["aspects"]]
    rows.append({"split": name, "sentences_with_aspects": len(with_aspects),
                 "mixed": sum(mixed(r) for r in with_aspects)})
table = pd.DataFrame(rows).set_index("split")
table["share_mixed"] = (table.mixed / table.sentences_with_aspects).round(3)
table"""),
        ("md", "## Most frequent aspect terms and their length"),
        ("code", """\
train_aspects = aspects[aspects.split == "train"]
top = {domain: group.term.value_counts().head(15) for domain, group in train_aspects.groupby("domain")}
display(pd.DataFrame({d: [f"{t} ({c})" for t, c in s.items()] for d, s in top.items()}))
print("words per aspect term (share):")
print(train_aspects.groupby("domain").words.value_counts(normalize=True).unstack(fill_value=0).round(3).iloc[:, :4])"""),
        ("md", "## Leakage check\n\nNo sentence text may appear in more than one split. `prepare_dataset` removes the overlaps it finds in the official files and fails if any remain; this cell repeats the check."),
        ("code", """\
texts = {name: {r["text"] for r in records} for name, records in splits.items()}
overlap = {f"{a} & {b}": len(texts[a] & texts[b]) for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
assert not any(overlap.values()), overlap
overlap"""),
    ],
    "02_preprocessing.ipynb": [
        ("md", "# 2. Preprocessing\n\nOne review followed through every step of `backend/app/nlp/preprocessing.py`, the code used for both training and inference."),
        ("code", SETUP),
        ("md", "## Cleaning and sentence splitting\n\nHTML, odd Unicode and extra whitespace are removed. Words are never removed or stemmed: BERT needs \"not\" and \"but\"."),
        ("code", """\
from app.nlp.preprocessing import clean_text, split_sentences, tokenize

raw = "  The <b>battery life</b> is great&nbsp;!!   But the touchpad isn\\u2019t responsive.\\n\\nWould not buy again. "
text = clean_text(raw)
print(repr(raw)); print(repr(text))
sentences = split_sentences(text)
pd.DataFrame({"sentence": s.text, "start": s.start, "end": s.end} for s in sentences)"""),
        ("md", "## Word tokens with character offsets\n\nThe offsets map a predicted aspect back to its position in the review, which the interface uses for highlighting."),
        ("code", """\
tokens = tokenize(sentences[0].text, sentences[0].start)
pd.DataFrame({"token": t.text, "start": t.start, "end": t.end} for t in tokens).T"""),
        ("md", "## BIO tags\n\nAnnotated character spans become one tag per word. `B-ASPECT` starts an aspect, `I-ASPECT` continues it."),
        ("code", """\
from app.nlp.preprocessing import bio_to_spans, spans_to_bio

sentence = "The battery life is great but the screen is dim."
words = tokenize(sentence)
gold = [(4, 16), (34, 40)]            # character spans of "battery life" and "screen"
tags = spans_to_bio(words, gold)
display(pd.DataFrame({"token": [w.text for w in words], "tag": tags}).T)
print("back to token spans (end exclusive):", bio_to_spans(tags))"""),
        ("md", "## Aligning word labels with BERT word-pieces\n\nBERT splits rare words into pieces. Only the first piece of a word keeps the label; the others and the special tokens get -100, which the loss ignores."),
        ("code", """\
from transformers import AutoTokenizer
from training.train_aspect import build_feature

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
record = {"tokens": ["The", "touchpad", "is", "unresponsive"], "tags": ["O", "B-ASPECT", "O", "O"]}
feature = build_feature(tokenizer, record, max_length=128)
pd.DataFrame({"piece": tokenizer.convert_ids_to_tokens(feature["input_ids"]), "label": feature["labels"]}).T"""),
        ("md", "## The two sentiment inputs\n\nThe aspect-sentiment model reads the sentence *and* the aspect; the overall model reads the sentence alone."),
        ("code", """\
from app.models.sentiment_model import encode_pair

for aspect in ("battery life", "screen", None):
    ids = encode_pair(tokenizer, sentence, aspect, 128)["input_ids"]
    print(f"{str(aspect):13s}", " ".join(tokenizer.convert_ids_to_tokens(ids)))"""),
        ("md", "## Context and aspect normalisation\n\nThe clause shown next to each aspect, and the form used to group aspects in the statistics."),
        ("code", """\
from app.nlp.preprocessing import extract_context, normalize_aspect

print(repr(extract_context(sentence, 4, 16)))
print(repr(extract_context(sentence, 34, 40)))
print({word: normalize_aspect(word) for word in ("Batteries", "battery", "Screens", "battery life")})"""),
    ],
    "03_model_evaluation.ipynb": [
        ("md", "# 3. Model evaluation\n\nReads what the evaluation scripts wrote. Run these first, from `backend/`:\n\n```\npython -m training.evaluate\npython -m training.baseline\npython -m training.error_analysis\n```"),
        ("code", SETUP),
        ("code", """\
import json
from app.paths import DOCS_DIR, MODELS_DIR

report = json.loads((MODELS_DIR / "evaluation_report.json").read_text(encoding="utf-8"))
print("generated:", report["generated_at"], "| test domains:", report["domains"])
pd.DataFrame({name: {
    "domains": ", ".join(log["hyperparameters"]["domains"]),
    "epochs": log["hyperparameters"]["epochs"],
    "best epoch": log["best_epoch"],
    "validation score": round(log["best_validation_score"], 4),
    "minutes": log["training_minutes"],
} for name, log in report["training"].items()})"""),
        ("md", "## Headline metrics per test domain"),
        ("code", """\
def headline(results):
    return {
        "aspect F1": results["aspect_extraction"]["f1"],
        "sentiment accuracy": results["aspect_sentiment"]["accuracy"],
        "sentiment macro-F1": results["aspect_sentiment"]["macro"]["f1"],
        "mixed-sentence accuracy": results["aspect_sentiment_by_sentence_type"]["mixed"]["accuracy"],
        "overall macro-F1": results["overall_sentiment"]["macro"]["f1"],
        "end-to-end F1": results["end_to_end"]["f1"],
    }

metrics = pd.DataFrame({scope: headline(r) for scope, r in report["results"].items()}).round(4)
display(metrics)
metrics.T.plot(kind="bar", figsize=(8, 3.8), rot=0, ylim=(0, 1), title="Test-set metrics")
plt.legend(fontsize=7, ncol=2); plt.tight_layout(); plt.show()"""),
        ("md", "## Per-class results and confusion matrix (aspect sentiment)\n\nNeutral is the hardest class."),
        ("code", """\
sentiment = report["results"]["all"]["aspect_sentiment"]
display(pd.DataFrame(sentiment["per_class"]).T.round(4))
confusion = sentiment["confusion_matrix"]
pd.DataFrame(confusion["matrix"], index=[f"true {l}" for l in confusion["labels"]],
             columns=[f"pred {l}" for l in confusion["labels"]])"""),
        ("code", """\
from IPython.display import Image, display as show
for name in ("sentiment_confusion_matrix.png", "overall_confusion_matrix.png"):
    show(Image(filename=str(DOCS_DIR / "figures" / name), width=420))"""),
        ("md", "## What BERT adds over a rule-and-lexicon baseline"),
        ("code", """\
baseline = json.loads((MODELS_DIR / "baseline_report.json").read_text(encoding="utf-8"))
paths = {"aspect F1": ("aspect_extraction", "f1"), "sentiment macro-F1": ("aspect_sentiment", "macro", "f1"),
         "overall macro-F1": ("overall_sentiment", "macro", "f1"), "end-to-end F1": ("end_to_end", "f1")}

def pick(results, path):
    for key in path:
        results = results[key]
    return results

comparison = pd.DataFrame({
    "baseline": {n: pick(baseline["results"]["all"], p) for n, p in paths.items()},
    "BERT": {n: pick(report["results"]["all"], p) for n, p in paths.items()},
}).round(4)
comparison["difference"] = (comparison.BERT - comparison.baseline).round(4)
display(comparison)
comparison[["baseline", "BERT"]].plot(kind="bar", figsize=(7, 3.5), rot=0, ylim=(0, 1), title="Baseline vs. BERT, both domains")
plt.tight_layout(); plt.show()"""),
        ("md", "## Error analysis and transfer\n\nThe full tables are in `docs/error_analysis.md` and `docs/transfer.md`."),
        ("code", """\
from IPython.display import Markdown
for name in ("error_analysis.md", "transfer.md"):
    path = DOCS_DIR / name
    text = path.read_text(encoding="utf-8") if path.exists() else f"`{name}` not found: run `python -m training.error_analysis`."
    show(Markdown(text))"""),
    ],
}


def main() -> None:
    for filename, cells in NOTEBOOKS.items():
        notebook = new_notebook(
            cells=[new_markdown_cell(s) if kind == "md" else new_code_cell(s) for kind, s in cells],
            metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                      "language_info": {"name": "python"}},
        )
        nbformat.write(notebook, HERE / filename)
        print("wrote", HERE / filename)


if __name__ == "__main__":
    main()
