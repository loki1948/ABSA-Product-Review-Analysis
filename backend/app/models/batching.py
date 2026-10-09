"""Padding and batched forward passes shared by both BERT models."""

from __future__ import annotations

from typing import Any

import torch

from app.nlp.labels import IGNORE_INDEX

Feature = dict[str, Any]


def pad_batch(
    features: list[Feature], pad_token_id: int, device: torch.device | None = None
) -> dict[str, torch.Tensor]:
    """Pad variable-length features to the longest sequence in the batch.

    Padding per batch (instead of to a fixed 512 tokens) is what keeps training
    and inference usable on a CPU: review sentences are short.
    """
    width = max(len(f["input_ids"]) for f in features)

    def padded(key: str, fill: int) -> torch.Tensor:
        return torch.tensor(
            [list(f[key]) + [fill] * (width - len(f[key])) for f in features], dtype=torch.long
        )

    batch = {"input_ids": padded("input_ids", pad_token_id), "attention_mask": padded("attention_mask", 0)}
    if "token_type_ids" in features[0]:
        batch["token_type_ids"] = padded("token_type_ids", 0)
    if "labels" in features[0]:
        if isinstance(features[0]["labels"], int):  # one label per sequence
            batch["labels"] = torch.tensor([f["labels"] for f in features], dtype=torch.long)
        else:  # one label per token
            batch["labels"] = padded("labels", IGNORE_INDEX)
    if device is not None:
        batch = {key: value.to(device) for key, value in batch.items()}
    return batch


@torch.inference_mode()
def predict_logits(
    model: torch.nn.Module,
    features: list[Feature],
    pad_token_id: int,
    batch_size: int = 32,
    device: torch.device | None = None,
) -> list[torch.Tensor]:
    """Run ``model`` over ``features`` and return one logits tensor per feature.

    Features are processed in length order (similar lengths share a batch, so
    little padding is wasted) and the results are returned in the input order.
    Token-classification logits are trimmed to each sequence's true length.
    """
    model.eval()
    order = sorted(range(len(features)), key=lambda i: len(features[i]["input_ids"]))
    results: list[torch.Tensor | None] = [None] * len(features)
    for offset in range(0, len(order), batch_size):
        chunk = order[offset : offset + batch_size]
        inputs = [{k: v for k, v in features[i].items() if k != "labels"} for i in chunk]
        logits = model(**pad_batch(inputs, pad_token_id, device)).logits.cpu()
        for row, index in enumerate(chunk):
            if logits.dim() == 3:
                results[index] = logits[row, : len(features[index]["input_ids"])]
            else:
                results[index] = logits[row]
    return results  # type: ignore[return-value]
