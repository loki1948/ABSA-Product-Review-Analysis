"""Label sets shared by training, evaluation and inference.

Keeping them in one place guarantees that the integer ids written into a saved
model always mean the same thing when the model is loaded again.
"""

from __future__ import annotations

# BIO scheme for aspect extraction:
#   B-ASPECT = first token of an aspect term
#   I-ASPECT = any following token of the same aspect term
#   O        = token that is not part of an aspect term
ASPECT_LABELS: list[str] = ["O", "B-ASPECT", "I-ASPECT"]
ASPECT_LABEL2ID: dict[str, int] = {label: i for i, label in enumerate(ASPECT_LABELS)}
ASPECT_ID2LABEL: dict[int, str] = dict(enumerate(ASPECT_LABELS))

SENTIMENT_LABELS: list[str] = ["negative", "neutral", "positive"]
SENTIMENT_LABEL2ID: dict[str, int] = {label: i for i, label in enumerate(SENTIMENT_LABELS)}
SENTIMENT_ID2LABEL: dict[int, str] = dict(enumerate(SENTIMENT_LABELS))

# PyTorch's cross-entropy loss skips positions carrying this label. We use it for
# [CLS]/[SEP]/[PAD] and for every word-piece after the first one of a word.
IGNORE_INDEX: int = -100
