"""Request and response models of the REST API.

This file is the contract with the frontend: ``frontend/src/types/api.ts``
mirrors it field for field. Change both together.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

Sentiment = Literal["positive", "negative", "neutral"]

MAX_REVIEW_CHARS = 5000
MAX_BATCH_REVIEWS = 50


class AnalyzeRequest(BaseModel):
    review: str = Field(
        min_length=1,
        max_length=MAX_REVIEW_CHARS,
        description="The product review to analyse.",
        examples=["The camera is excellent but the battery life is poor."],
    )
    save: bool = Field(default=True, description="Store the result in the review history.")

    @field_validator("review")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review must not be blank")
        return value


class BatchAnalyzeRequest(BaseModel):
    reviews: list[str] = Field(
        min_length=1,
        max_length=MAX_BATCH_REVIEWS,
        description="The product reviews to analyse, one string per review.",
        examples=[["The camera is excellent.", "The battery life is poor."]],
    )
    save: bool = Field(default=True, description="Store the results in the review history.")

    @field_validator("reviews")
    @classmethod
    def _each_review_valid(cls, value: list[str]) -> list[str]:
        for position, review in enumerate(value):
            if not review.strip():
                raise ValueError(f"review {position} must not be blank")
            if len(review) > MAX_REVIEW_CHARS:
                raise ValueError(f"review {position} is longer than {MAX_REVIEW_CHARS} characters")
        return value


class AspectResult(BaseModel):
    aspect: str = Field(description="Aspect term exactly as written in the review.")
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1, description="Probability of the predicted sentiment.")
    context: str = Field(description="Clause of the review that talks about the aspect.")
    start: int = Field(description="Start character offset of the aspect in `review`.")
    end: int = Field(description="End character offset (exclusive) of the aspect in `review`.")


class AnalysisResponse(BaseModel):
    id: int | None = Field(description="History id; null when the request had save=false.")
    review: str = Field(description="The review text that was analysed (whitespace-normalised).")
    overall_sentiment: Sentiment
    overall_confidence: float = Field(ge=0, le=1)
    aspects: list[AspectResult]
    created_at: datetime | None

    @field_serializer("created_at")
    def _as_utc(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:  # SQLite returns naive datetimes; they are stored in UTC
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()


class BatchAnalysisResponse(BaseModel):
    total: int = Field(description="Number of reviews analysed.")
    items: list[AnalysisResponse] = Field(description="One result per review, in request order.")


class ReviewListResponse(BaseModel):
    total: int = Field(description="Number of stored reviews matching the filter.")
    limit: int
    offset: int
    items: list[AnalysisResponse]


class SentimentCounts(BaseModel):
    positive: int
    negative: int
    neutral: int


class AspectStatistics(SentimentCounts):
    aspect: str = Field(description="Normalised aspect (lowercase, singular).")
    total: int


class StatisticsResponse(BaseModel):
    total_reviews: int
    total_aspects: int
    overall_sentiment_distribution: SentimentCounts
    aspect_sentiment_distribution: SentimentCounts
    top_aspects: list[AspectStatistics]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    models_loaded: bool
    database: bool
    detail: str | None = Field(description="Why the service is degraded, if it is.")


class ModelInfoResponse(BaseModel):
    """Evaluation report produced by ``python -m training.evaluate``."""

    report: dict[str, Any]
