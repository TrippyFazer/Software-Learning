"""Database engine, session factory, and the declarative base.

Sync SQLAlchemy on purpose: this is a single-learner application, and sync
code is both sufficient and considerably easier to read while learning
(ADR-0001, ADR-0006).
"""

from collections.abc import Generator
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.settings import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for every model in the application."""


def utcnow() -> datetime:
    """Timezone-aware UTC now — the only timestamp the database ever stores."""
    from datetime import UTC

    return datetime.now(UTC)


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one database session per request, always closed."""
    db = get_sessionmaker()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
