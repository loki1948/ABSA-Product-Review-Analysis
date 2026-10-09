from __future__ import annotations

from pathlib import Path

from training.common import sentence_level_label
from training.metrics import classification_metrics, span_prf
from training.prepare_dataset import parse_semeval_xml, split_train_val

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sentences>
  <sentence id="1">
    <text>The battery life is great but the screen is dim.</text>
    <aspectTerms>
      <aspectTerm term="battery life" polarity="positive" from="4" to="16"/>
      <aspectTerm term="screen" polarity="negative" from="34" to="40"/>
      <aspectTerm term="screen" polarity="negative" from="34" to="40"/>
      <aspectTerm term="oops" polarity="positive" from="90" to="99"/>
    </aspectTerms>
  </sentence>
  <sentence id="2"><text>I bought it last week.</text></sentence>
  <sentence id="3"><text>   </text></sentence>
</sentences>
"""


def test_parse_semeval_xml_validates_and_tags(tmp_path: Path) -> None:
    path = tmp_path / "sample.xml"
    path.write_text(SAMPLE_XML, encoding="utf-8")
    records, issues = parse_semeval_xml(path, "laptops")

    assert [r["id"] for r in records] == ["laptops:1", "laptops:2"]
    first = records[0]
    assert [(a["term"], a["polarity"]) for a in first["aspects"]] == [
        ("battery life", "positive"),
        ("screen", "negative"),
    ]
    assert first["tokens"][:4] == ["The", "battery", "life", "is"]
    assert first["tags"][:4] == ["O", "B-ASPECT", "I-ASPECT", "O"]
    assert first["tags"][first["tokens"].index("screen")] == "B-ASPECT"
    assert len(first["tokens"]) == len(first["tags"])
    assert records[1]["aspects"] == [] and set(records[1]["tags"]) == {"O"}
    assert issues == {
        "duplicate_term_dropped": 1,
        "bad_offsets_dropped": 1,
        "empty_sentence_dropped": 1,
    }


def test_split_is_deterministic_and_disjoint() -> None:
    records = [{"id": f"d:{i}"} for i in range(100)]
    train_a, val_a = split_train_val(records, 0.1, seed=42)
    train_b, val_b = split_train_val(list(reversed(records)), 0.1, seed=42)
    assert (train_a, val_a) == (train_b, val_b)
    assert len(val_a) == 10 and len(train_a) == 90
    assert not {r["id"] for r in train_a} & {r["id"] for r in val_a}


def test_sentence_level_label() -> None:
    assert sentence_level_label(["positive", "positive", "negative"]) == "positive"
    assert sentence_level_label(["negative", "neutral"]) == "negative"
    assert sentence_level_label(["positive", "negative"]) == "neutral"
    assert sentence_level_label(["neutral"]) == "neutral"
    assert sentence_level_label(["conflict"]) is None
    assert sentence_level_label([]) is None


def test_span_prf_requires_exact_boundaries() -> None:
    gold = [{(1, 3), (5, 6)}, set()]
    predicted = [{(1, 3), (5, 7)}, {(0, 1)}]
    metrics = span_prf(gold, predicted)
    assert metrics["true_positives"] == 1
    assert metrics["precision"] == 1 / 3
    assert metrics["recall"] == 1 / 2
    assert abs(metrics["f1"] - 0.4) < 1e-9


def test_span_prf_with_nothing_predicted() -> None:
    assert span_prf([{(0, 1)}], [set()])["f1"] == 0.0


def test_classification_metrics() -> None:
    labels = ["negative", "neutral", "positive"]
    metrics = classification_metrics(
        ["positive", "positive", "negative", "neutral"],
        ["positive", "negative", "negative", "neutral"],
        labels,
    )
    assert metrics["accuracy"] == 0.75
    assert metrics["confusion_matrix"]["matrix"] == [[1, 0, 0], [0, 1, 0], [1, 0, 1]]
    assert metrics["per_class"]["positive"] == {"precision": 1.0, "recall": 0.5, "f1": 2 / 3, "support": 2}
