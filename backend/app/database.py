"""Database utilities using SQLModel."""
from __future__ import annotations

from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import get_settings

_settings = get_settings()
engine = create_engine(_settings.database_url, echo=False)


def init_db() -> None:
    """Create database tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session():  # pragma: no cover - FastAPI dependency hook
    with Session(engine) as session:
        yield session
