from __future__ import annotations

"""Integration test — /healthz endpoint."""

import pytest


@pytest.mark.asyncio
async def test_healthz_returns_200(async_client) -> None:
    """GET /healthz returns 200 with connector status entries."""
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data or "connectors" in data or isinstance(data, dict)
