"""Test harness: real PostgreSQL (a dedicated *_test database), real content.

Environment is pinned BEFORE any app import so Settings' lru_cache and the
lazy engine pick up test values.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

os.environ.update(
    {
        "APP_ENV": "test",
        "POSTGRES_DB": "learninglab_test",
        "POSTGRES_USER": os.environ.get("POSTGRES_USER", "learninglab"),
        "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "learninglab"),
        "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "CONTENT_ROOT": str(REPO_ROOT / "content"),
        "CONTENT_HOT_RELOAD": "false",
        "SESSION_SECRET": "test-secret-not-production",
        "LOGIN_MAX_ATTEMPTS": "5",
    }
)

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.db import Base, get_engine, get_sessionmaker  # noqa: E402
from app.core.settings import get_settings  # noqa: E402

# Import model modules so their tables register on Base.metadata before
# create_all / TRUNCATE enumerate them.
from app.modules.auth import models as _auth_models  # noqa: E402, F401
from app.modules.learning import models as _learning_models  # noqa: E402, F401


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create the test database (once) and its schema."""
    s = get_settings()
    admin = psycopg.connect(
        host=s.postgres_host,
        port=s.postgres_port,
        user=s.postgres_user,
        password=s.postgres_password,
        dbname="postgres",
        autocommit=True,
    )
    exists = admin.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (s.postgres_db,)
    ).fetchone()
    if not exists:
        admin.execute(f'CREATE DATABASE "{s.postgres_db}"')
    admin.close()

    Base.metadata.create_all(get_engine())
    yield


@pytest.fixture(autouse=True)
def clean_tables(test_database):
    """Every test starts with empty tables (schema kept)."""
    with get_engine().begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db_session():
    with get_sessionmaker()() as session:
        yield session
        session.commit()


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


TEST_EMAIL = "tester@example.com"
TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def user(db_session):
    from app.modules.auth import service

    u = service.create_user(db_session, TEST_EMAIL, TEST_PASSWORD, "Tester")
    db_session.commit()
    return u


@pytest.fixture
def auth_client(client, user):
    """A TestClient that is already logged in (cookie set)."""
    res = client.post(
        "/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert res.status_code == 200
    return client
