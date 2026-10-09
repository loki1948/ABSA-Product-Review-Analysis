"""Review history and aggregate statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import review_to_response
from app.database import crud
from app.database.database import get_db
from app.schemas.analysis import (
    AnalysisResponse,
    ReviewListResponse,
    Sentiment,
    StatisticsResponse,
)

router = APIRouter(tags=["reviews"])


@router.get("/reviews", response_model=ReviewListResponse)
def list_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sentiment: Sentiment | None = Query(None, description="Filter by overall sentiment."),
    db: Session = Depends(get_db),
) -> ReviewListResponse:
    """Previously analysed reviews, newest first."""
    total, reviews = crud.list_reviews(db, limit, offset, sentiment)
    return ReviewListResponse(
        total=total, limit=limit, offset=offset, items=[review_to_response(r) for r in reviews]
    )


@router.get("/reviews/{review_id}", response_model=AnalysisResponse)
def get_review(review_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    review = crud.get_review(db, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review not found.")
    return review_to_response(review)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: Session = Depends(get_db)) -> Response:
    if not crud.delete_review(db, review_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/statistics", response_model=StatisticsResponse)
def statistics(
    top_n: int = Query(10, ge=1, le=50, description="How many of the most frequent aspects."),
    db: Session = Depends(get_db),
) -> StatisticsResponse:
    """Sentiment and aspect aggregates over the whole review history."""
    return StatisticsResponse(**crud.get_statistics(db, top_n))
