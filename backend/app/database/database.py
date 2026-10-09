"""SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class of all ORM models."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        url = get_settings().database_url
        # FastAPI serves requests from a thread pool; SQLite needs this flag to
        # allow a connection to be used outside the thread that created it.
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Forget the current engine so the next use re-reads the settings (tests)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine, _session_factory = None, None


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    from app.database import models  # noqa: F401  (registers the tables on Base)

    Base.metadata.create_all(get_engine())


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    get_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
