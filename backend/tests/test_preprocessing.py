from __future__ import annotations

from app.nlp.preprocessing import (
    bio_to_spans,
    clean_text,
    extract_context,
    normalize_aspect,
    spans_to_bio,
    split_sentences,
    tokenize,
)


def test_clean_text_normalises_without_losing_words() -> None:
    raw = "  The <b>camera</b>   is&nbsp;not\tgood.\n\nBattery​ life is OK!  "
    assert clean_text(raw) == "The camera is not good. Battery life is OK!"


def test_clean_text_keeps_stop_words_and_negation() -> None:
    assert clean_text("It is not good") == "It is not good"


def test_tokenize_offsets_point_back_into_the_text() -> None:
    text = "Battery life isn't great, sadly."
    tokens = tokenize(text)
    assert [t.text for t in tokens][:3] == ["Battery", "life", "isn"]
    assert all(text[t.start : t.end] == t.text for t in tokens)


def test_tokenize_applies_offset() -> None:
    assert tokenize("good", offset=10)[0].start == 10


def test_split_sentences_keeps_offsets() -> None:
    text = "The camera is great. The battery is bad! Would I buy it again?"
    sentences = split_sentences(text)
    assert [s.text for s in sentences] == [
        "The camera is great.",
        "The battery is bad!",
        "Would I buy it again?",
    ]
    assert all(text[s.start : s.end] == s.text for s in sentences)


def test_split_sentences_empty_text() -> None:
    assert split_sentences("") == []


def test_spans_to_bio_single_and_multi_word() -> None:
    text = "The battery life and screen are great"
    tokens = tokenize(text)
    spans = [(text.index("battery"), text.index("life") + 4), (text.index("screen"), text.index("screen") + 6)]
    assert spans_to_bio(tokens, spans) == ["O", "B-ASPECT", "I-ASPECT", "O", "B-ASPECT", "O", "O"]


def test_spans_to_bio_adjacent_aspects_stay_separate() -> None:
    tokens = tokenize("screen keyboard")
    assert spans_to_bio(tokens, [(0, 6), (7, 15)]) == ["B-ASPECT", "B-ASPECT"]


def test_spans_to_bio_snaps_partial_word_to_whole_token() -> None:
    tokens = tokenize("batteries")
    assert spans_to_bio(tokens, [(0, 7)]) == ["B-ASPECT"]


def test_bio_to_spans() -> None:
    tags = ["O", "B-ASPECT", "I-ASPECT", "O", "B-ASPECT", "B-ASPECT"]
    assert bio_to_spans(tags) == [(1, 3), (4, 5), (5, 6)]


def test_bio_to_spans_tolerates_i_without_b() -> None:
    assert bio_to_spans(["I-ASPECT", "I-ASPECT", "O"]) == [(0, 2)]


def test_bio_round_trip() -> None:
    text = "Great touch pad, poor battery life."
    tokens = tokenize(text)
    spans = [(6, 15), (22, 34)]
    recovered = [(tokens[a].start, tokens[b - 1].end) for a, b in bio_to_spans(spans_to_bio(tokens, spans))]
    assert recovered == spans


def test_extract_context_returns_the_aspects_clause() -> None:
    sentence = "The phone has an amazing camera, a bright display, but the battery backup is terrible."
    start = sentence.index("battery backup")
    assert extract_context(sentence, start, start + 14) == "the battery backup is terrible"
    start = sentence.index("display")
    assert extract_context(sentence, start, start + 7) == "a bright display"
    start = sentence.index("camera")
    assert extract_context(sentence, start, start + 6) == "The phone has an amazing camera"


def test_extract_context_without_boundaries_is_whole_sentence() -> None:
    assert extract_context("The screen is sharp.", 4, 10) == "The screen is sharp"


def test_normalize_aspect_lowercases_and_collapses_spaces() -> None:
    assert normalize_aspect("Battery   Life") == "battery life"


def test_split_sentences_attaches_stray_punctuation_to_the_previous_sentence() -> None:
    text = "The battery life is great !! But the screen is dim."
    sentences = split_sentences(text)
    assert [s.text for s in sentences] == ["The battery life is great !!", "But the screen is dim."]
    assert all(text[s.start : s.end] == s.text for s in sentences)


def test_split_sentences_drops_leading_punctuation_only_text() -> None:
    assert [s.text for s in split_sentences("!!! Great screen.")] == ["Great screen."]
    assert split_sentences("?!") == []
