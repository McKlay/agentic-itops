from __future__ import annotations

"""Shared pytest fixtures for the backend test suite.

Usage::

    async def test_something(async_client, seeded_store):
        response = await async_client.post("/api/chat", json={...})
        assert response.status_code == 200
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force auth bypass and offline mode before any app imports
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("STORAGE_BACKEND", "memory")

from app.main import create_app  # noqa: E402 — must be after env var setup
from app.store.memory import InMemoryStore  # noqa: E402
from app.config import Settings  # noqa: E402


# ---------------------------------------------------------------------------
# Shared Settings fixture (lightweight — only env vars, no side effects)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(auth_disabled=True, storage_backend="memory")


# ---------------------------------------------------------------------------
# Seeded in-memory store (function-scoped so each test gets a fresh copy)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def seeded_store() -> InMemoryStore:
    store = InMemoryStore()
    await store.seed()
    return store


# ---------------------------------------------------------------------------
# Full app + ASGI client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def async_client():
    """Yield an ``httpx.AsyncClient`` wired to the full ASGI app.

    The app lifespan is explicitly triggered via ``app.router.lifespan_context``
    so that ``app.state.orchestrator`` (and other startup objects) are populated
    before any requests are made.  ``AUTH_DISABLED=true`` is pre-set so the JWT
    middleware accepts any bearer token.
    """
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer test-dev-token"},
        ) as client:
            yield client
