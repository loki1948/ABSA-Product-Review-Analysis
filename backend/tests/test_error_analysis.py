from __future__ import annotations

from training.error_analysis import (
    accuracy_by_band,
    confidence_band,
    extraction_outcomes,
    render_transfer,
)


def test_exact_match_is_correct() -> None:
    outcome = extraction_outcomes({(1, 3)}, {(1, 3)})
    assert outcome == {"correct": [(1, 3)], "boundary": [], "missed": [], "spurious": []}


def test_overlap_without_exact_match_is_a_boundary_error() -> None:
    # gold "battery life" (1, 3), predicted only "battery" (1, 2)
    outcome = extraction_outcomes({(1, 3)}, {(1, 2)})
    assert outcome["boundary"] == [(1, 3)]
    assert outcome["missed"] == [] and outcome["spurious"] == [] and outcome["correct"] == []


def test_gold_aspect_with_no_overlapping_prediction_is_missed() -> None:
    assert extraction_outcomes({(1, 3)}, set())["missed"] == [(1, 3)]


def test_prediction_overlapping_no_gold_aspect_is_spurious() -> None:
    outcome = extraction_outcomes({(1, 3)}, {(1, 3), (6, 7)})
    assert outcome["spurious"] == [(6, 7)]
    assert outcome["correct"] == [(1, 3)]


def test_adjacent_spans_do_not_overlap() -> None:
    outcome = extraction_outcomes({(1, 3)}, {(3, 4)})
    assert outcome["missed"] == [(1, 3)] and outcome["spurious"] == [(3, 4)]


def test_confidence_band_edges() -> None:
    assert confidence_band(0.59) == "below 0.60"
    assert confidence_band(0.60) == "0.60 to 0.80"
    assert confidence_band(0.7999) == "0.60 to 0.80"
    assert confidence_band(0.80) == "0.80 and above"
    assert confidence_band(1.0) == "0.80 and above"


def test_accuracy_is_reported_per_band_in_order() -> None:
    rows = accuracy_by_band([(0.5, True), (0.55, False), (0.9, True), (0.95, True)])
    assert rows == [
        ("below 0.60", 2, 0.5),
        ("0.60 to 0.80", 0, None),
        ("0.80 and above", 2, 1.0),
    ]


def scope(aspect_f1: float, sentiment_f1: float) -> dict:
    return {
        "test_sentences": 800,
        "aspect_extraction": {"f1": aspect_f1},
        "aspect_sentiment": {"accuracy": sentiment_f1, "macro": {"f1": sentiment_f1}},
        "end_to_end": {"f1": aspect_f1 * sentiment_f1},
    }


def test_transfer_table_compares_out_of_domain_with_in_domain_training() -> None:
    laptops_only = {"results": {"laptops": scope(0.79, 0.73), "restaurants": scope(0.50, 0.60)}}
    both = {"results": {"laptops": scope(0.80, 0.74), "restaurants": scope(0.85, 0.75)}}
    text = render_transfer(laptops_only, both, samples=[])
    assert "| Aspect extraction F1 | 0.5000 | 0.8500 | +0.3500 |" in text
    assert "| Aspect extraction F1 | 0.7900 | 0.8000 | +0.0100 |" in text


def test_transfer_lists_the_hand_written_reviews_as_an_illustration() -> None:
    reports = {"results": {"laptops": scope(0.8, 0.7), "restaurants": scope(0.8, 0.7)}}
    samples = [("phones", "The camera is superb.", "positive", [("camera", "positive", 0.97)])]
    text = render_transfer(reports, reports, samples)
    assert "| phones | The camera is superb. | positive | camera (positive, 97%) |" in text
    assert "not a measurement" in text
