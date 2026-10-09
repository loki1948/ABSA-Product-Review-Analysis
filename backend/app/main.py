"""FastAPI application.

Run from the ``backend`` directory:

    uvicorn app.main:app --reload

Interactive API documentation is then served at http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analysis, health, reviews
from app.config import get_settings
from app.database.database import init_db
from app.nlp.pipeline import ABSAPipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: create the tables and load the BERT models once."""
    settings = get_settings()
    init_db()
    app.state.pipeline = None
    app.state.model_error = None
    if settings.load_models:
        try:
            app.state.pipeline = ABSAPipeline.from_pretrained(
                settings.aspect_model_dir,
                settings.sentiment_model_dir,
                settings.overall_model_dir,
                settings.max_length,
            )
            logger.info("Models loaded.")
        except Exception as exc:
            # Keep serving: history and statistics still work, and /api/health
            # tells the frontend what is wrong.
            app.state.model_error = str(exc)
            logger.exception("Could not load the models; /api/analyze will return 503.")
    else:
        app.state.model_error = "Model loading is disabled (ABSA_LOAD_MODELS=false)."
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Extracts product aspects from a review and the sentiment towards each one.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (analysis.router, reviews.router, health.router):
        app.include_router(router, prefix="/api")

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    return app


app = create_app()
