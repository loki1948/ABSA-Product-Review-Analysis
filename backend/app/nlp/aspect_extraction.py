"""Pipeline stages 3 and 4: aspect extraction and aspect-context identification."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.aspect_model import AspectExtractor
from app.nlp.preprocessing import Sentence, bio_to_spans, extract_context, tokenize


@dataclass(frozen=True)
class ExtractedAspect:
    """An aspect term found in a review.

    ``start``/``end`` are character offsets into the full (cleaned) review.
    ``sentence`` is the sentence the aspect occurs in and ``context`` the clause
    of that sentence around the aspect.
    """

    text: str
    start: int
    end: int
    confidence: float
    sentence: str
    context: str


def extract_aspects(
    extractor: AspectExtractor, text: str, sentences: list[Sentence]
) -> list[ExtractedAspect]:
    """Find all aspect terms in ``sentences`` (which are slices of ``text``).

    The BERT tagger labels every word with B-ASPECT / I-ASPECT / O; consecutive
    aspect tags are merged into one multi-word aspect ("battery life") and
    mapped back to character offsets. No aspect vocabulary is involved: what
    counts as an aspect is decided by the model from context.
    """
    token_lists = [tokenize(sentence.text, offset=sentence.start) for sentence in sentences]
    predictions = extractor.predict([[token.text for token in tokens] for tokens in token_lists])

    aspects: list[ExtractedAspect] = []
    for sentence, tokens, tags in zip(sentences, token_lists, predictions):
        for first, last in bio_to_spans([tag.tag for tag in tags]):
            start, end = tokens[first].start, tokens[last - 1].end
            surface = text[start:end]
            if not any(char.isalnum() for char in surface):
                continue  # a span made only of punctuation is never an aspect
            span_tags = tags[first:last]
            aspects.append(
                ExtractedAspect(
                    text=surface,
                    start=start,
                    end=end,
                    confidence=sum(tag.confidence for tag in span_tags) / len(span_tags),
                    sentence=sentence.text,
                    context=extract_context(
                        sentence.text, start - sentence.start, end - sentence.start
                    ),
                )
            )
    return aspects
