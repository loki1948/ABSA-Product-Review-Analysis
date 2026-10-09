"""Database tables.

One review has many aspect sentiments (one-to-many), so aspects live in their
own table instead of being squeezed into a column of ``reviews``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_text: Mapped[str] = mapped_column(Text)
    overall_sentiment: Mapped[str] = mapped_column(String(16), index=True)
    overall_confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, index=True)

    aspects: Mapped[list["AspectSentiment"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="AspectSentiment.id"
    )


class AspectSentiment(Base):
    __tablename__ = "aspect_sentiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    aspect: Mapped[str] = mapped_column(String(255))  # as written in the review
    # Lowercased + lemmatised form, so "Batteries" and "battery" aggregate together.
    aspect_normalized: Mapped[str] = mapped_column(String(255), index=True)
    sentiment: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    context: Mapped[str] = mapped_column(Text)
    # Character offsets of the aspect inside Review.review_text.
    start_char: Mapped[int] = mapped_column(Integer)
    end_char: Mapped[int] = mapped_column(Integer)

    review: Mapped[Review] = relationship(back_populates="aspects")
