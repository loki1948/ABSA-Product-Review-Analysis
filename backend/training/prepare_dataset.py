"""Download, validate and split the SemEval-2014 Task 4 ABSA dataset.

Run from the ``backend`` directory:

    python -m training.prepare_dataset

Outputs (all under ``data/processed``):

* ``train.jsonl`` / ``val.jsonl`` / ``test.jsonl`` - one sentence per line with
  its aspect terms, character offsets, polarities, word tokens and BIO tags.
* ``sentiment_{split}.csv`` - one (review, aspect, sentiment) row per aspect
  term: the human-readable view of the sentiment-classification data.
* ``dataset_stats.json`` - counts computed from the files above.

The official test set ("gold") is used as the test split. The validation split
is carved out of the official training data, per domain, with a fixed seed.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from app.nlp.preprocessing import spans_to_bio, tokenize
from app.paths import PROCESSED_DATA_DIR, RAW_DATA_DIR

logger = logging.getLogger("prepare_dataset")

_HF = "https://huggingface.co/datasets/alexcadillon/SemEval2014Task4/resolve/main"
_TRAIN_DIR = "SemEval'14-ABSA-TrainData_v2%20%26%20AnnotationGuidelines"
_GH = (
    "https://raw.githubusercontent.com/davidsbatista/Aspect-Based-Sentiment-Analysis"
    "/master/datasets/ABSA-SemEval2014"
)

# (domain, official split) -> local file name and mirrors, tried in order.
SOURCES: dict[tuple[str, str], dict[str, Any]] = {
    ("laptops", "train"): {
        "file": "Laptop_Train_v2.xml",
        "urls": [f"{_HF}/{_TRAIN_DIR}/Laptop_Train_v2.xml", f"{_GH}/Laptop_Train_v2.xml"],
    },
    ("restaurants", "train"): {
        "file": "Restaurants_Train_v2.xml",
        "urls": [
            f"{_HF}/{_TRAIN_DIR}/Restaurants_Train_v2.xml",
            f"{_GH}/Restaurants_Train_v2.xml",
        ],
    },
    ("laptops", "test"): {
        "file": "Laptops_Test_Gold.xml",
        "urls": [f"{_HF}/ABSA_Gold_TestData/Laptops_Test_Gold.xml"],
    },
    ("restaurants", "test"): {
        "file": "Restaurants_Test_Gold.xml",
        "urls": [f"{_HF}/ABSA_Gold_TestData/Restaurants_Test_Gold.xml"],
    },
}

VALID_POLARITIES = {"positive", "negative", "neutral", "conflict"}
# "conflict" (both positive and negative about one aspect) is rare and is
# conventionally excluded from 3-class sentiment classification. Those terms
# are still used as aspects for the extraction model.
SENTIMENT_POLARITIES = {"positive", "negative", "neutral"}


def download(file_name: str, urls: list[str], raw_dir: Path) -> Path:
    """Fetch ``file_name`` into ``raw_dir`` unless it is already there."""
    target = raw_dir / file_name
    if target.exists() and target.stat().st_size > 0:
        logger.info("Using cached %s", target.name)
        return target
    raw_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for url in urls:
        try:
            logger.info("Downloading %s", url)
            request = urllib.request.Request(url, headers={"User-Agent": "absa-project"})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            ET.fromstring(payload)  # refuse anything that is not well-formed XML
            target.write_bytes(payload)
            return target
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError(
        f"Could not download {file_name}. Place it manually in {raw_dir}.\n" + "\n".join(errors)
    )


def parse_semeval_xml(path: Path, domain: str) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Parse one SemEval-2014 XML file into sentence records, validating as we go."""
    issues: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    for sentence in ET.parse(path).getroot().iter("sentence"):
        text = sentence.findtext("text") or ""
        if not text.strip():
            issues["empty_sentence_dropped"] += 1
            continue

        aspects: list[dict[str, Any]] = []
        seen: set[tuple[int, int]] = set()
        for term in sentence.iter("aspectTerm"):
            start, end = int(term.get("from", -1)), int(term.get("to", -1))
            polarity = term.get("polarity", "")
            if not 0 <= start < end <= len(text):
                issues["bad_offsets_dropped"] += 1
                continue
            if polarity not in VALID_POLARITIES:
                issues["unknown_polarity_dropped"] += 1
                continue
            if (start, end) in seen:
                issues["duplicate_term_dropped"] += 1
                continue
            if text[start:end] != term.get("term"):
                # Offsets are authoritative; the surface string is re-read from the text.
                issues["term_text_mismatch_fixed"] += 1
            seen.add((start, end))
            aspects.append(
                {"term": text[start:end], "from": start, "to": end, "polarity": polarity}
            )

        aspects.sort(key=lambda a: a["from"])
        tokens = tokenize(text)
        records.append(
            {
                "id": f"{domain}:{sentence.get('id')}",
                "domain": domain,
                "text": text,
                "aspects": aspects,
                "tokens": [t.text for t in tokens],
                "tags": spans_to_bio(tokens, [(a["from"], a["to"]) for a in aspects]),
            }
        )
    return records, issues


def _text_key(record: dict[str, Any]) -> str:
    """Whitespace- and case-insensitive identity of a sentence."""
    return " ".join(record["text"].lower().split())


def split_train_val(
    records: list[dict[str, Any]], val_fraction: float, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Seeded sentence-level split, so no sentence is shared between train and val."""
    shuffled = sorted(records, key=lambda r: r["id"])
    random.Random(seed).shuffle(shuffled)
    n_val = round(len(shuffled) * val_fraction)
    return shuffled[n_val:], shuffled[:n_val]


def describe(records: list[dict[str, Any]]) -> dict[str, Any]:
    polarity = Counter(a["polarity"] for r in records for a in r["aspects"])
    return {
        "sentences": len(records),
        "sentences_with_aspects": sum(1 for r in records if r["aspects"]),
        "aspect_terms": sum(len(r["aspects"]) for r in records),
        "polarity": dict(sorted(polarity.items())),
        "avg_tokens_per_sentence": round(
            sum(len(r["tokens"]) for r in records) / max(len(records), 1), 2
        ),
    }


def write_split(name: str, records: list[dict[str, Any]], out_dir: Path) -> None:
    with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    rows = [
        {"id": r["id"], "domain": r["domain"], "review": r["text"], "aspect": a["term"],
         "from": a["from"], "to": a["to"], "sentiment": a["polarity"]}
        for r in records
        for a in r["aspects"]
        if a["polarity"] in SENTIMENT_POLARITIES
    ]
    pd.DataFrame(rows).to_csv(out_dir / f"sentiment_{name}.csv", index=False, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=PROCESSED_DATA_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parsed: dict[tuple[str, str], list[dict[str, Any]]] = {}
    issues: dict[str, dict[str, int]] = {}
    for key, source in SOURCES.items():
        path = download(source["file"], source["urls"], args.raw_dir)
        parsed[key], file_issues = parse_semeval_xml(path, key[0])
        issues[source["file"]] = dict(file_issues)

    # The official files are not perfectly disjoint: a few training sentences
    # also occur in the gold test set. The test set is never modified; instead
    # those sentences (and exact duplicates) are removed from the training data.
    test_texts = {_text_key(r) for key, recs in parsed.items() if key[1] == "test" for r in recs}
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    seen_texts: set[str] = set()  # shared by both domains
    for (domain, official_split), records in parsed.items():
        if official_split == "test":
            splits["test"] += records
            continue
        file_issues = issues[SOURCES[(domain, official_split)]["file"]]
        kept: list[dict[str, Any]] = []
        for record in records:
            key = _text_key(record)
            if key in test_texts:
                file_issues["also_in_test_set_dropped"] = (
                    file_issues.get("also_in_test_set_dropped", 0) + 1
                )
            elif key in seen_texts:
                file_issues["duplicate_sentence_dropped"] = (
                    file_issues.get("duplicate_sentence_dropped", 0) + 1
                )
            else:
                seen_texts.add(key)
                kept.append(record)
        train, val = split_train_val(kept, args.val_fraction, args.seed)
        splits["train"] += train
        splits["val"] += val

    # Guard against leakage: no sentence text may be shared between splits.
    keys = {name: {_text_key(r) for r in records} for name, records in splits.items()}
    if keys["train"] & keys["val"] or keys["train"] & keys["test"] or keys["val"] & keys["test"]:
        raise RuntimeError("Sentences overlap between splits.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {
        "dataset": "SemEval-2014 Task 4 (Aspect Based Sentiment Analysis)",
        "seed": args.seed,
        "val_fraction": args.val_fraction,
        "validation_issues": issues,
        "splits": {},
    }
    for name, records in splits.items():
        write_split(name, records, args.out_dir)
        stats["splits"][name] = {
            "all": describe(records),
            **{d: describe([r for r in records if r["domain"] == d])
               for d in sorted({r["domain"] for r in records})},
        }
    (args.out_dir / "dataset_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
