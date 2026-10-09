from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import crud
from app.database.database import Base
from app.database.models import AspectSentiment, Review
from app.nlp.pipeline import AnalysisResult, AspectSentimentResult


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


def _result(review: str, overall: str, aspects: list[tuple[str, str]]) -> AnalysisResult:
    return AnalysisResult(
        review=review,
        overall_sentiment=overall,
        overall_confidence=0.8,
        aspects=[
            AspectSentimentResult(
                aspect=name, sentiment=sentiment, confidence=0.9, context=f"about {name}",
                start=0, end=len(name), extraction_confidence=0.7,
            )
            for name, sentiment in aspects
        ],
    )


def test_review_is_stored_with_one_row_per_aspect(db: Session) -> None:
    stored = crud.create_review(
        db, _result("r1", "positive", [("Camera", "positive"), ("battery life", "negative")])
    )
    assert stored.id is not None and stored.created_at is not None
    assert [(a.aspect, a.aspect_normalized, a.sentiment) for a in stored.aspects] == [
        ("Camera", "camera", "positive"),
        ("battery life", "battery life", "negative"),
    ]
    assert all(a.review_id == stored.id for a in stored.aspects)


def test_review_without_aspects_can_be_stored(db: Session) -> None:
    stored = crud.create_review(db, _result("nothing here", "neutral", []))
    assert crud.get_review(db, stored.id).aspects == []


def test_deleting_a_review_deletes_its_aspects(db: Session) -> None:
    stored = crud.create_review(db, _result("r1", "positive", [("screen", "positive")]))
    assert crud.delete_review(db, stored.id) is True
    assert crud.delete_review(db, stored.id) is False
    assert db.scalar(select(func.count(Review.id))) == 0
    assert db.scalar(select(func.count(AspectSentiment.id))) == 0


def test_list_reviews_filters_and_counts(db: Session) -> None:
    crud.create_review(db, _result("a", "positive", []))
    crud.create_review(db, _result("b", "negative", []))
    crud.create_review(db, _result("c", "positive", []))

    total, reviews = crud.list_reviews(db, limit=1, offset=0, sentiment="positive")
    assert total == 2 and [r.review_text for r in reviews] == ["c"]
    total, reviews = crud.list_reviews(db, limit=10, offset=1)
    assert total == 3 and [r.review_text for r in reviews] == ["b", "a"]


def test_statistics_group_by_normalised_aspect(db: Session) -> None:
    crud.create_review(db, _result("a", "positive", [("Screen", "positive"), ("price", "neutral")]))
    crud.create_review(db, _result("b", "negative", [("screen", "negative")]))

    stats = crud.get_statistics(db)
    assert stats["total_reviews"] == 2 and stats["total_aspects"] == 3
    assert stats["overall_sentiment_distribution"] == {"negative": 1, "neutral": 0, "positive": 1}
    assert stats["aspect_sentiment_distribution"] == {"negative": 1, "neutral": 1, "positive": 1}
    assert stats["top_aspects"][0] == {
        "aspect": "screen", "total": 2, "positive": 1, "negative": 1, "neutral": 0,
    }
