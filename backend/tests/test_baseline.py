from __future__ import annotations

import pytest

from training.baseline import (
    LexiconClassifier,
    evaluate_baseline,
    noun_runs,
    render_markdown,
)

POSITIVE = {"great", "gorgeous", "good"}
NEGATIVE = {"terrible", "slow", "bad"}


@pytest.fixture
def classifier() -> LexiconClassifier:
    return LexiconClassifier(POSITIVE, NEGATIVE)


def test_single_noun_is_one_aspect() -> None:
    assert noun_runs(["DT", "NN", "VBZ", "JJ"]) == [(1, 2)]


def test_consecutive_nouns_form_one_aspect() -> None:
    #        The   battery life  is     great
    assert noun_runs(["DT", "NN", "NN", "VBZ", "JJ"]) == [(1, 3)]


def test_separated_nouns_are_separate_aspects() -> None:
    #        screen and  keyboards
    assert noun_runs(["NN", "CC", "NNS"]) == [(0, 1), (2, 3)]


def test_sentence_without_nouns_has_no_aspects() -> None:
    assert noun_runs(["PRP", "VBZ", "JJ"]) == []


def test_proper_nouns_and_pronouns_are_not_aspects() -> None:
    assert noun_runs(["NNP", "VBZ", "PRP"]) == []


def test_opinion_word_in_the_aspect_clause_decides(classifier: LexiconClassifier) -> None:
    text = "The screen is gorgeous but the battery life is terrible."
    assert classifier.predict([text, text], ["screen", "battery life"]) == ["positive", "negative"]


def test_no_opinion_word_is_neutral(classifier: LexiconClassifier) -> None:
    assert classifier.predict(["It has a screen."], ["screen"]) == ["neutral"]


def test_negation_flips_the_opinion(classifier: LexiconClassifier) -> None:
    assert classifier.predict(["The screen is not good."], ["screen"]) == ["negative"]
    assert classifier.predict(["The screen isn't bad."], ["screen"]) == ["positive"]


def test_distant_negation_does_not_flip(classifier: LexiconClassifier) -> None:
    text = "I did not expect that the big new screen would be so good."
    assert classifier.predict([text], ["screen"]) == ["positive"]


def test_without_an_aspect_the_whole_sentence_counts(classifier: LexiconClassifier) -> None:
    text = "The screen is gorgeous but the battery life is terrible and slow."
    assert classifier.predict([text], [None]) == ["negative"]


def test_matching_ignores_letter_case(classifier: LexiconClassifier) -> None:
    assert classifier.predict(["GREAT screen"], ["screen"]) == ["positive"]


RECORDS = [
    {
        "id": "laptops:1", "domain": "laptops",
        "text": "The screen is great.",
        "tokens": ["The", "screen", "is", "great", "."],
        "tags": ["O", "B-ASPECT", "O", "O", "O"],
        "aspects": [{"term": "screen", "from": 4, "to": 10, "polarity": "positive"}],
    },
    {
        "id": "restaurants:1", "domain": "restaurants",
        "text": "The service was terrible.",
        "tokens": ["The", "service", "was", "terrible", "."],
        "tags": ["O", "B-ASPECT", "O", "O", "O"],
        "aspects": [{"term": "service", "from": 4, "to": 11, "polarity": "negative"}],
    },
]
TAGS = {
    "The screen is great.": ["DT", "NN", "VBZ", "JJ", "."],
    "The service was terrible.": ["DT", "NN", "VBD", "JJ", "."],
}


def fake_tagger(tokens: list[str]) -> list[str]:
    return TAGS[" ".join(tokens[:-1]) + tokens[-1]]


def test_report_has_the_layout_of_the_bert_report(classifier: LexiconClassifier) -> None:
    results = evaluate_baseline(RECORDS, fake_tagger, classifier)
    assert set(results) == {
        "test_sentences", "aspect_extraction", "aspect_sentiment",
        "overall_sentiment", "end_to_end",
    }
    assert results["aspect_extraction"]["f1"] == 1.0
    assert results["aspect_sentiment"]["accuracy"] == 1.0
    assert results["end_to_end"]["f1"] == 1.0


def test_markdown_puts_baseline_and_bert_side_by_side(classifier: LexiconClassifier) -> None:
    scope = evaluate_baseline(RECORDS, fake_tagger, classifier)
    baseline = {"generated_at": "2026-10-10T00:00:00+00:00", "domains": ["laptops", "restaurants"],
                "results": {"all": scope}}
    bert = {"results": {"all": {**scope, "aspect_extraction": {**scope["aspect_extraction"], "f1": 0.5}}}}
    text = render_markdown(baseline, bert)
    assert "| Aspect extraction F1 | 1.0000 | 0.5000 | -0.5000 |" in text
    assert "Hu and Liu" in text


def test_markdown_without_a_bert_report_still_lists_the_baseline(classifier: LexiconClassifier) -> None:
    scope = evaluate_baseline(RECORDS, fake_tagger, classifier)
    text = render_markdown({"generated_at": "x", "domains": ["laptops"], "results": {"all": scope}}, None)
    assert "| Aspect extraction F1 | 1.0000 | n/a | n/a |" in text
