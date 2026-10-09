"""POST /api/analyze and /api/analyze/batch - run the ABSA pipeline on reviews."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_pipeline, result_to_response, review_to_response
from app.database import crud
from app.database.database import get_db
from app.nlp.pipeline import ABSAPipeline
from app.schemas.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    BatchAnalysisResponse,
    BatchAnalyzeRequest,
)

router = APIRouter(tags=["analysis"])


# Declared with plain `def`: FastAPI then runs it in a worker thread, so the
# (CPU-heavy) model inference does not block the server's event loop.
@router.post("/analyze", response_model=AnalysisResponse)
def analyze_review(
    payload: AnalyzeRequest,
    pipeline: ABSAPipeline = Depends(get_pipeline),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Extract the aspects of a review and classify the sentiment of each one."""
    result = pipeline.analyze(payload.review)
    if not payload.save:
        return result_to_response(result)
    return review_to_response(crud.create_review(db, result))


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
def analyze_reviews(
    payload: BatchAnalyzeRequest,
    pipeline: ABSAPipeline = Depends(get_pipeline),
    db: Session = Depends(get_db),
) -> BatchAnalysisResponse:
    """Analyse several reviews in one request; results keep the request order."""
    results = [pipeline.analyze(review) for review in payload.reviews]
    if payload.save:
        items = [review_to_response(crud.create_review(db, result)) for result in results]
    else:
        items = [result_to_response(result) for result in results]
    return BatchAnalysisResponse(total=len(items), items=items)
