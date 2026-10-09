"""Evaluation metrics. Every number in the project report comes from here."""

from __future__ import annotations

from typing import Any, Hashable, Sequence

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support


def span_prf(gold: Sequence[set[Hashable]], predicted: Sequence[set[Hashable]]) -> dict[str, Any]:
    """Exact-match precision / recall / F1 over sets of items, micro-averaged.

    For aspect extraction an item is a span ``(first_token, last_token)``: a
    prediction only counts when BOTH boundaries match the annotation, which is
    the SemEval evaluation criterion. Predicting "battery" when the gold aspect
    is "battery life" is one false positive and one false negative.
    """
    tp = sum(len(g & p) for g, p in zip(gold, predicted))
    n_predicted = sum(len(p) for p in predicted)
    n_gold = sum(len(g) for g in gold)
    precision = tp / n_predicted if n_predicted else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "predicted": n_predicted,
        "gold": n_gold,
    }


def classification_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: list[str]
) -> dict[str, Any]:
    """Accuracy, macro/weighted and per-class P/R/F1, and the confusion matrix."""
    result: dict[str, Any] = {
        "support": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }
    for average in ("macro", "weighted"):
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, average=average, zero_division=0
        )
        result[average] = {"precision": float(precision), "recall": float(recall), "f1": float(f1)}
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    result["per_class"] = {
        label: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i, label in enumerate(labels)
    }
    # Rows = true label, columns = predicted label, both in ``labels`` order.
    result["confusion_matrix"] = {
        "labels": labels,
        "matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }
    return result
