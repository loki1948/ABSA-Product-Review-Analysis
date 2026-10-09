"""Service health and model evaluation report."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.paths import MODELS_DIR
from app.schemas.analysis import HealthResponse, ModelInfoResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

EVALUATION_REPORT = MODELS_DIR / "evaluation_report.json"


@router.get("/health", response_model=HealthResponse)
def health(request: Request, db: Session = Depends(get_db)) -> HealthResponse:
    """`ok` when the models are loaded and the database answers."""
    models_loaded = getattr(request.app.state, "pipeline", None) is not None
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        logger.exception("Database health check failed")
        database_ok = False

    detail: str | None = None
    if not models_loaded:
        detail = getattr(request.app.state, "model_error", None) or "Models are not loaded."
    elif not database_ok:
        detail = "Database is not reachable."
    return HealthResponse(
        status="ok" if models_loaded and database_ok else "degraded",
        models_loaded=models_loaded,
        database=database_ok,
        detail=detail,
    )


@router.get("/model-info", response_model=ModelInfoResponse)
def model_info() -> ModelInfoResponse:
    """Test-set metrics of the deployed models, as measured by the evaluation script."""
    if not EVALUATION_REPORT.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No evaluation report yet. Run: python -m training.evaluate",
        )
    return ModelInfoResponse(report=json.loads(EVALUATION_REPORT.read_text(encoding="utf-8")))
