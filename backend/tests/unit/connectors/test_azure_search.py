from __future__ import annotations

"""Unit tests — AzureSearchConnector fallback mode.

Validates that the offline connector returns correctly-shaped results
using the ka-vector index schema (chunk, title, chunk_id, score).
"""

import pytest

from app.config import Settings
from app.connectors.azure_search import AzureSearchConnector, _MIN_SCORE


@pytest.fixture()
def connector() -> AzureSearchConnector:
    conn = AzureSearchConnector(Settings(auth_disabled=True, storage_backend="memory"))
    conn._live = False
    conn._client = None
    return conn


@pytest.mark.asyncio
async def test_fallback_returns_results(connector: AzureSearchConnector) -> None:
    """Fallback search returns at least one result for a keyword query."""
    results = await connector.search(query="SAP SSO login failures", top_k=5)
    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_fallback_result_schema(connector: AzureSearchConnector) -> None:
    """Each fallback result has the ka-vector schema: chunk, title, chunk_id, score."""
    results = await connector.search(query="SAP", top_k=5)
    for r in results:
        assert "chunk" in r, f"Missing 'chunk': {r.keys()}"
        assert "title" in r, f"Missing 'title': {r.keys()}"
        assert "chunk_id" in r, f"Missing 'chunk_id': {r.keys()}"
        assert "score" in r, f"Missing 'score': {r.keys()}"
        assert isinstance(r["score"], float)
        # Fallback scores should be realistic RRF-range (we set them ≥ 0.025)
        assert r["score"] >= _MIN_SCORE, f"Fallback score {r['score']} < _MIN_SCORE"


@pytest.mark.asyncio
async def test_fallback_get_article_by_chunk_id(connector: AzureSearchConnector) -> None:
    """get_article returns the correct fallback chunk by chunk_id."""
    article = await connector.get_article("ka_0001_chunk_0")
    assert article is not None
    assert article["chunk_id"] == "ka_0001_chunk_0"
    assert "SAP" in article["chunk"]


@pytest.mark.asyncio
async def test_fallback_get_article_not_found(connector: AzureSearchConnector) -> None:
    """get_article returns None for a non-existent chunk_id."""
    result = await connector.get_article("nonexistent_id")
    assert result is None


@pytest.mark.asyncio
async def test_fallback_respects_top_k(connector: AzureSearchConnector) -> None:
    """Fallback search respects the top_k limit."""
    results = await connector.search(query="runbook latency troubleshooting", top_k=1)
    assert len(results) <= 1
