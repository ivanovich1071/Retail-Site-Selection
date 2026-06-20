"""Shared pytest fixtures for integration tests.

Tests run against a real PostgreSQL+PostGIS instance (the app uses asyncpg,
which — unlike psycopg2 — is unaffected by the Windows locale decode bug).
If no database is reachable, DB-dependent tests are skipped automatically so
`pytest backend/tests/` still succeeds on a machine without Docker.
"""
import asyncio
import os
import socket
import sys
from uuid import uuid4

import pytest

# Windows' default ProactorEventLoop breaks asyncpg sockets (WinError 64).
# Switch to the selector loop so TestClient's anyio portal uses a compatible loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Point the app at the local test instances BEFORE importing any app module.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "retail_test_db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("SECRET_KEY", "test-secret-key")


def _tcp_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


DB_HOST = os.environ["POSTGRES_HOST"]
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_AVAILABLE = _tcp_open(DB_HOST, DB_PORT)

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE, reason=f"PostgreSQL not reachable at {DB_HOST}:{DB_PORT}"
)


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient backed by the real app.

    The app's module-level engine uses a QueuePool whose connections get bound
    to the import-time event loop. TestClient runs requests in a separate portal
    loop, which breaks pooled asyncpg connections. Override get_db with a
    NullPool engine so every session opens a fresh connection in the active loop.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import NullPool

    from backend.main import app
    from backend.app.core.config import settings
    from backend.app.core.database import get_db

    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
    """Register a fresh user and return a valid JWT access token."""
    email = f"test_{uuid4().hex[:8]}@eurotor.by"
    password = "secret1234"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Pytest User"},
    )
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
