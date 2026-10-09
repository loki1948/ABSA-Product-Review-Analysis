from __future__ import annotations

import pytest

from app.nlp.aspect_extraction import extract_aspects
from app.nlp.preprocessing import split_sentences
from tests.conftest import StubExtractor, requires_models


def test_extract_aspects_merges_multiword_terms_and_keeps_offsets() -> None:
    text = "The battery life is poor. I love the Camera!"
    aspects = extract_aspects(StubExtractor(), text, split_sentences(text))  # type: ignore[arg-type]

    assert [a.text for a in aspects] == ["battery life", "Camera"]
    assert all(text[a.start : a.end] == a.text for a in aspects)
    assert aspects[0].sentence == "The battery life is poor."
    assert aspects[1].sentence == "I love the Camera!"
    assert aspects[0].confidence == pytest.approx(0.85)  # mean of 0.9 and 0.8


def test_extract_aspects_gives_each_aspect_its_own_context() -> None:
    text = "Great camera, but the battery is terrible."
    aspects = extract_aspects(StubExtractor(), text, split_sentences(text))  # type: ignore[arg-type]
    assert {a.text: a.context for a in aspects} == {
        "camera": "Great camera",
        "battery": "the battery is terrible",
    }


def test_extract_aspects_no_aspects() -> None:
    text = "I bought it yesterday."
    assert extract_aspects(StubExtractor(), text, split_sentences(text)) == []  # type: ignore[arg-type]


@pytest.mark.model
@requires_models
def test_training_labels_align_with_word_pieces(real_pipeline) -> None:
    from app.nlp.labels import ASPECT_LABEL2ID, IGNORE_INDEX
    from training.train_aspect import build_feature

    tokenizer = real_pipeline.extractor.tokenizer
    record = {"tokens": ["The", "touchpad", "is", "great"], "tags": ["O", "B-ASPECT", "O", "O"]}
    feature = build_feature(tokenizer, record, max_length=32)

    assert len(feature["labels"]) == len(feature["input_ids"])
    assert feature["labels"][0] == IGNORE_INDEX and feature["labels"][-1] == IGNORE_INDEX
    # Exactly one label per word survives, in order; the rest is ignored.
    kept = [label for label in feature["labels"] if label != IGNORE_INDEX]
    assert kept == [ASPECT_LABEL2ID[tag] for tag in record["tags"]]


@pytest.mark.model
@requires_models
def test_model_tags_one_prediction_per_word(real_pipeline) -> None:
    sentences = [["The", "battery", "life", "is", "excellent", "."], [], ["Nice", "screen"]]
    predictions = real_pipeline.extractor.predict(sentences)
    assert [len(p) for p in predictions] == [6, 0, 2]
    assert all(0.0 <= tag.confidence <= 1.0 for sentence in predictions for tag in sentence)


@pytest.mark.model
@requires_models
def test_model_finds_an_aspect_it_was_never_given_a_list_of(real_pipeline) -> None:
    text = "The battery life is excellent."
    aspects = extract_aspects(real_pipeline.extractor, text, split_sentences(text))
    assert any("battery" in a.text.lower() for a in aspects)
