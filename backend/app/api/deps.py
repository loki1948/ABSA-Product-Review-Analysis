"""Dependencies and converters shared by the API routes."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.database.models import Review
from app.nlp.pipeline import ABSAPipeline, AnalysisResult
from app.schemas.analysis import AnalysisResponse, AspectResult


def get_pipeline(request: Request) -> ABSAPipeline:
    """The loaded ABSA pipeline, or HTTP 503 if the models are not available."""
    pipeline: ABSAPipeline | None = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        reason = getattr(request.app.state, "model_error", None) or "Models are not loaded."
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=reason)
    return pipeline


def result_to_response(result: AnalysisResult) -> AnalysisResponse:
    """Response for an analysis that was not saved."""
    return AnalysisResponse(
        id=None,
        review=result.review,
        overall_sentiment=result.overall_sentiment,  # type: ignore[arg-type]
        overall_confidence=result.overall_confidence,
        aspects=[
            AspectResult(
                aspect=a.aspect, sentiment=a.sentiment,  # type: ignore[arg-type]
                confidence=a.confidence, context=a.context, start=a.start, end=a.end,
            )
            for a in result.aspects
        ],
        created_at=None,
    )


def review_to_response(review: Review) -> AnalysisResponse:
    """Response for a stored review (fresh analysis or history entry)."""
    return AnalysisResponse(
        id=review.id,
        review=review.review_text,
        overall_sentiment=review.overall_sentiment,  # type: ignore[arg-type]
        overall_confidence=review.overall_confidence,
        aspects=[
            AspectResult(
                aspect=a.aspect, sentiment=a.sentiment,  # type: ignore[arg-type]
                confidence=a.confidence, context=a.context, start=a.start_char, end=a.end_char,
            )
            for a in review.aspects
        ],
        created_at=review.created_at,
    )
