"""Text preprocessing shared by the training scripts and the inference pipeline.

Design note (important for the viva): BERT is a *contextual* model. Classic
preprocessing steps such as stop-word removal, stemming or stripping punctuation
destroy exactly the context it relies on ("not good" -> "good"). So this module
only does light, meaning-preserving normalisation:

* ``clean_text``       - Unicode normalisation, HTML/control-character removal,
                         whitespace collapsing.
* ``split_sentences``  - sentence segmentation (NLTK Punkt), because the models
                         are trained on single sentences.
* ``tokenize``         - word-level tokenisation that keeps character offsets,
                         so predictions can be mapped back onto the review.
* ``spans_to_bio`` / ``bio_to_spans`` - conversion between aspect character
                         spans and BIO tags.
* ``normalize_aspect`` - lowercasing + lemmatisation, used ONLY to group aspects
                         in statistics ("Batteries" and "battery" count together).

Lowercasing is done by the ``bert-base-uncased`` tokenizer itself.
"""

from __future__ import annotations

import html
import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]{1,200}>")
_CONTROL_RE = re.compile(r"[\u0000-\u001f\u007f-\u009f​-‏﻿]")
_WHITESPACE_RE = re.compile(r"\s+")
# A token is either a run of word characters or one single punctuation symbol.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")
_SENTENCE_FALLBACK_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
# Places where one opinion usually ends and another begins.
_CLAUSE_BOUNDARY_RE = re.compile(
    r"[,;:()]|\s-\s|\b(?:but|however|although|though|whereas|while|yet|except)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Token:
    """A word-level token with its character offsets in the source text."""

    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Sentence:
    """A sentence with its character offsets in the source text."""

    text: str
    start: int
    end: int


def clean_text(text: str) -> str:
    """Normalise a raw review without removing linguistic information."""
    text = unicodedata.normalize("NFKC", text)
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _CONTROL_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def tokenize(text: str, offset: int = 0) -> list[Token]:
    """Split ``text`` into word-level tokens.

    ``offset`` is added to every position, which lets the caller tokenise one
    sentence and still get offsets relative to the whole review.
    """
    return [
        Token(m.group(), m.start() + offset, m.end() + offset) for m in _TOKEN_RE.finditer(text)
    ]


@lru_cache(maxsize=1)
def _punkt_span_tokenizer() -> Callable[[str], list[tuple[int, int]]] | None:
    """Return NLTK's Punkt span tokenizer, downloading its data once if needed."""
    try:
        import nltk
        from nltk.tokenize.punkt import PunktTokenizer

        try:
            tokenizer = PunktTokenizer("english")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)
            tokenizer = PunktTokenizer("english")
        return lambda text: list(tokenizer.span_tokenize(text))
    except Exception as exc:  # no network, broken install, ...
        logger.warning("NLTK Punkt unavailable (%s); using regex sentence splitter.", exc)
        return None


def split_sentences(text: str) -> list[Sentence]:
    """Segment ``text`` into sentences, keeping character offsets."""
    span_tokenize = _punkt_span_tokenizer()
    if span_tokenize is not None:
        spans = span_tokenize(text)
    else:
        spans = [m.span() for m in _SENTENCE_FALLBACK_RE.finditer(text)]

    sentences: list[Sentence] = []
    for start, end in spans:
        raw = text[start:end]
        stripped = raw.strip()
        if not stripped:
            continue
        start += len(raw) - len(raw.lstrip())
        sentences.append(Sentence(stripped, start, start + len(stripped)))
    return sentences


def spans_to_bio(tokens: list[Token], spans: list[tuple[int, int]]) -> list[str]:
    """Convert aspect character spans into one BIO tag per token.

    A token belongs to an aspect when it overlaps the aspect's character span,
    so annotations that start or end in the middle of a word are snapped
    outwards to whole tokens.
    """
    tags = ["O"] * len(tokens)
    for span_start, span_end in sorted(spans):
        inside = False
        for i, token in enumerate(tokens):
            if token.start < span_end and token.end > span_start:
                if tags[i] != "O":  # overlapping annotation: keep the first one
                    continue
                tags[i] = "I-ASPECT" if inside else "B-ASPECT"
                inside = True
    return tags


def bio_to_spans(tags: list[str]) -> list[tuple[int, int]]:
    """Convert BIO tags into ``(first_token, last_token_exclusive)`` spans.

    Decoding is lenient: an ``I-ASPECT`` that does not follow another aspect tag
    (which a model can produce) simply starts a new span.
    """
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for i, tag in enumerate(tags):
        if tag == "B-ASPECT" or (tag == "I-ASPECT" and start is None):
            if start is not None:
                spans.append((start, i))
            start = i
        elif tag == "O" and start is not None:
            spans.append((start, i))
            start = None
    if start is not None:
        spans.append((start, len(tags)))
    return spans


def extract_context(sentence: str, start: int, end: int) -> str:
    """Return the clause of ``sentence`` that contains the aspect at ``[start, end)``.

    Example: for "great camera, but the battery is terrible" and the aspect
    "battery" this returns "the battery is terrible". Offsets are relative to
    ``sentence``. Clause boundaries that fall inside the aspect are ignored.
    """
    left, right = 0, len(sentence)
    for match in _CLAUSE_BOUNDARY_RE.finditer(sentence):
        if match.end() <= start:
            left = match.end()
        elif match.start() >= end:
            right = match.start()
            break
    context = sentence[left:right].strip(" \t.!?")
    return context or sentence.strip()


@lru_cache(maxsize=1)
def _lemmatizer() -> Callable[[str], str] | None:
    try:
        import nltk
        from nltk.stem import WordNetLemmatizer

        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet", quiet=True)
        lemmatizer = WordNetLemmatizer()
        lemmatizer.lemmatize("batteries")  # forces the corpus to load now
        return lambda word: lemmatizer.lemmatize(word, pos="n")
    except Exception as exc:
        logger.warning("WordNet lemmatizer unavailable (%s); aspects are only lowercased.", exc)
        return None


@lru_cache(maxsize=4096)
def normalize_aspect(aspect: str) -> str:
    """Canonical form of an aspect for grouping: lowercase, last word lemmatised."""
    words = _WHITESPACE_RE.sub(" ", aspect.lower()).strip().split(" ")
    lemmatize = _lemmatizer()
    if lemmatize is not None and words and words[-1].isalpha():
        words[-1] = lemmatize(words[-1])
    return " ".join(words)
