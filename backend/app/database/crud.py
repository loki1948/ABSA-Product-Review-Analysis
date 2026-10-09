"""Database operations used by the API routes."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.database.models import AspectSentiment, Review
from app.nlp.labels import SENTIMENT_LABELS
from app.nlp.pipeline import AnalysisResult
from app.nlp.preprocessing import normalize_aspect


def create_review(db: Session, result: AnalysisResult) -> Review:
    """Store one analysis: the review row plus one row per aspect."""
    review = Review(
        review_text=result.review,
        overall_sentiment=result.overall_sentiment,
        overall_confidence=result.overall_confidence,
        aspects=[
            AspectSentiment(
                aspect=a.aspect,
                aspect_normalized=normalize_aspect(a.aspect),
                sentiment=a.sentiment,
                confidence=a.confidence,
                context=a.context,
                start_char=a.start,
                end_char=a.end,
            )
            for a in result.aspects
        ],
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: int) -> Review | None:
    return db.get(Review, review_id)


def list_reviews(
    db: Session, limit: int = 20, offset: int = 0, sentiment: str | None = None
) -> tuple[int, list[Review]]:
    """Newest-first page of stored reviews and the total number of matches."""
    query = select(Review)
    count_query = select(func.count(Review.id))
    if sentiment:
        query = query.where(Review.overall_sentiment == sentiment)
        count_query = count_query.where(Review.overall_sentiment == sentiment)
    total = db.scalar(count_query) or 0
    reviews = db.scalars(
        query.options(selectinload(Review.aspects))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return total, list(reviews)


def delete_review(db: Session, review_id: int) -> bool:
    review = db.get(Review, review_id)
    if review is None:
        return False
    db.delete(review)  # ORM cascade removes its aspect rows too
    db.commit()
    return True


def _distribution(rows: Any) -> dict[str, int]:
    counts = {label: 0 for label in SENTIMENT_LABELS}
    counts.update({label: count for label, count in rows if label in counts})
    return counts


def get_statistics(db: Session, top_n: int = 10) -> dict[str, Any]:
    """Aggregates for the dashboard charts."""
    overall = db.execute(
        select(Review.overall_sentiment, func.count(Review.id)).group_by(Review.overall_sentiment)
    ).all()
    by_aspect_sentiment = db.execute(
        select(AspectSentiment.sentiment, func.count(AspectSentiment.id)).group_by(
            AspectSentiment.sentiment
        )
    ).all()

    def count_of(label: str) -> Any:
        return func.sum(case((AspectSentiment.sentiment == label, 1), else_=0))

    total = func.count(AspectSentiment.id)
    top = db.execute(
        select(
            AspectSentiment.aspect_normalized,
            total,
            count_of("positive"),
            count_of("negative"),
            count_of("neutral"),
        )
        .group_by(AspectSentiment.aspect_normalized)
        .order_by(total.desc(), AspectSentiment.aspect_normalized)
        .limit(top_n)
    ).all()

    return {
        "total_reviews": db.scalar(select(func.count(Review.id))) or 0,
        "total_aspects": db.scalar(select(func.count(AspectSentiment.id))) or 0,
        "overall_sentiment_distribution": _distribution(overall),
        "aspect_sentiment_distribution": _distribution(by_aspect_sentiment),
        "top_aspects": [
            {
                "aspect": aspect,
                "total": int(n),
                "positive": int(positive),
                "negative": int(negative),
                "neutral": int(neutral),
            }
            for aspect, n, positive, negative, neutral in top
        ],
    }
