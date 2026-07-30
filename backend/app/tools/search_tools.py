from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.connectors.azure_search import AzureSearchConnector
    from app.connectors.azure_openai import AzureOpenAIConnector
    from app.config import Settings

logger = logging.getLogger(__name__)


def make_search_tools(
    search: "AzureSearchConnector",
    openai: "AzureOpenAIConnector",
    settings: "Settings | None" = None,  # reserved for future SAS URL generation
):
    """Return (hybrid_search, get_article) handler closures bound to the given connectors.

    Call once at startup and register the returned handlers in ``ToolRegistry``.
    """

    async def hybrid_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Hybrid BM25+vector search over the knowledge base.

        1. Embed the query via AzureOpenAIConnector (falls back to zero vector offline).
        2. Pass both query text and vector to AzureSearchConnector.search().
        3. Return ranked result list: [{chunk, title, chunk_id, score}, ...].

        If embedding fails the vector is set to ``None`` so the connector
        degrades gracefully to keyword-only (BM25) search.
        """
        logger.debug("hybrid_search query=%r top_k=%d", query, top_k)
        try:
            vector = await openai.embed(query)
        except Exception:
            logger.warning("Embedding failed — falling back to keyword-only search")
            vector = None
        results = await search.search(query=query, vector=vector, top_k=top_k)
        logger.debug("hybrid_search returned %d results", len(results))
        return results

    async def get_article(article_id: str) -> dict[str, Any] | None:
        """Fetch the full text of a KB article by its document ID."""
        logger.debug("get_article id=%r", article_id)
        return await search.get_article(article_id)

    return hybrid_search, get_article
