from __future__ import annotations

import logging
import time
from typing import Any

from app.config import Settings
from app.connectors.base import ConnectorBase, ConnectorHealth

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vector field name in the ka-vector Azure AI Search index
# (text-embedding-3-small, 1536 dimensions)
# ---------------------------------------------------------------------------
_VECTOR_FIELD = "text_vector"
_EMBEDDING_DIM = 1536

# ---------------------------------------------------------------------------
# Minimum RRF hybrid-search score for a chunk to be returned.
#
# Calibrated from a 25-query benchmark (2026-04-29) against the ka-vector
# index using hybrid BM25 + vector (RRF) search — no semantic reranker.
#
# Observed @search.score distribution across 125 retrieved chunks:
#   Relevant   chunks (n=66): min=0.0274  median=0.0328  max=0.0333
#   Irrelevant chunks (n=59): min=0.0159  median=0.0293  max=0.0325
#
# Threshold 0.025 retains ALL observed relevant chunks and drops the
# low-noise irrelevant tail.  Borderline chunks in the 0.025–0.033
# overlap band are kept — they are typically near-miss chunks from the
# correct KA, not off-topic content.
#
# NOTE: Do NOT compare with the legacy 0.55 BM25-only threshold.
# BM25 TF-IDF scores (0.5–3.0) are a different scale from RRF (0.01–0.04).
# ---------------------------------------------------------------------------
_MIN_SCORE: float = 0.025

# ---------------------------------------------------------------------------
# Fallback KB article chunks used when Azure AI Search is not configured.
# Schema mirrors the live ka-vector index so all downstream code uses the
# same field names: chunk, title, chunk_id, score.
# ---------------------------------------------------------------------------
_FALLBACK_ARTICLES: list[dict[str, Any]] = [
    {
        "chunk_id": "ka_0001_chunk_0",
        "title": "KB0001001.pdf",
        "chunk": (
            "SAP Single Sign-On Troubleshooting Guide. "
            "Step-by-step guide for resolving SAP SSO failures including SAML assertion "
            "errors, certificate expiry, and Active Directory trust issues. "
            "Key steps: 1) Check IdP certificate on ADFS console. "
            "2) Verify SP metadata in SAP SICF. "
            "3) Review SAML trace in browser dev tools."
        ),
        "score": 0.0333,
    },
    {
        "chunk_id": "ka_0002_chunk_0",
        "title": "KB0001002.pdf",
        "chunk": (
            "Azure AD Conditional Access — MFA Registration Exemption Procedure. "
            "Procedure to temporarily exempt device groups from conditional access during "
            "MFA enrollment windows. Requires Global Administrator or Conditional Access "
            "Administrator role. Steps: Create named location for onboarding subnet, "
            "add exclusion to policy, set 24-hour window, remove after enrollment."
        ),
        "score": 0.0320,
    },
    {
        "chunk_id": "ka_0003_chunk_0",
        "title": "KB0001003.pdf",
        "chunk": (
            "MPLS Latency Runbook — DC Interconnect. "
            "Runbook for diagnosing high latency on P&G MPLS circuits. "
            "Tools: SolarWinds NTA, Cisco IOSXE traceroute, NetScope. "
            "Common causes: BGP route flap, QoS misconfiguration, physical layer errors. "
            "Escalation path: NOC L1 → Network Ops L2 → Carrier TAC."
        ),
        "score": 0.0310,
    },
]


class AzureSearchConnector(ConnectorBase):
    """Hybrid search connector — BM25 keyword + vector cosine via Azure AI Search.

    Index schema (``ka-vector``):
        - ``chunk``       : main text content of the chunk
        - ``title``       : source PDF filename (e.g. ``KB0626662.pdf``)
        - ``chunk_id``    : unique identifier per chunk
        - ``parent_id``   : ID of the parent document
        - ``text_vector`` : 1536-dim embedding vector (text-embedding-3-small)

    Returns top-*k* results with ``@search.score`` mapped to ``score``.
    Applies a minimum RRF score threshold of {_MIN_SCORE} to filter noise.

    Fallback: keyword substring match over ``_FALLBACK_ARTICLES`` so the
    knowledge agent returns useful results even without a live Search endpoint.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._client = None

        if settings.azure_search_endpoint and settings.azure_search_api_key:
            try:
                from azure.core.credentials import AzureKeyCredential
                from azure.search.documents import SearchClient

                self._client = SearchClient(
                    endpoint=settings.azure_search_endpoint,
                    index_name=settings.azure_search_index_name,
                    credential=AzureKeyCredential(settings.azure_search_api_key),
                )
                self._live = True
                self.logger.info(
                    "AzureSearchConnector live — endpoint=%s index=%s",
                    settings.azure_search_endpoint,
                    settings.azure_search_index_name,
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("AzureSearchConnector init failed: %s", exc)
        else:
            self.logger.warning(
                "AzureSearchConnector offline — AZURE_SEARCH_ENDPOINT or "
                "AZURE_SEARCH_API_KEY not set. Using fallback articles."
            )

    async def search(
        self,
        query: str,
        vector: list[float] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Execute a hybrid search and return ranked result dicts.

        Each result dict contains::

            chunk     – text content of the chunk
            title     – source PDF filename (e.g. KB0626662.pdf)
            chunk_id  – unique chunk identifier
            score     – RRF fusion score (typical 0.01–0.04)

        Chunks below the calibrated ``_MIN_SCORE`` threshold are dropped.
        """
        if not self._require_live("search"):
            return self._fallback_search(query, top_k)

        assert self._client is not None
        search_kwargs: dict[str, Any] = dict(
            search_text=query,
            select=["chunk", "title", "chunk_id"],
            top=top_k,
        )
        if vector:
            from azure.search.documents.models import VectorizedQuery

            search_kwargs["vector_queries"] = [
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=top_k,
                    fields=_VECTOR_FIELD,
                )
            ]

        try:
            results = self._client.search(**search_kwargs)
            chunks = [
                {
                    "chunk": r.get("chunk", ""),
                    "title": r.get("title", ""),
                    "chunk_id": r.get("chunk_id", ""),
                    "score": r.get("@search.score", 0.0),
                }
                for r in results
            ]
        except Exception:
            self.logger.exception("Azure AI Search request failed")
            return []

        # Apply calibrated RRF score threshold
        filtered = [c for c in chunks if c["score"] >= _MIN_SCORE]
        if len(filtered) < len(chunks):
            self.logger.debug(
                "Dropped %d/%d chunk(s) below score threshold %.4f",
                len(chunks) - len(filtered),
                len(chunks),
                _MIN_SCORE,
            )
        return filtered

    async def get_article(self, article_id: str) -> dict[str, Any] | None:
        """Fetch a single article/chunk by its ``chunk_id``."""
        if not self._require_live("get_article"):
            return next(
                (a for a in _FALLBACK_ARTICLES if a["chunk_id"] == article_id),
                None,
            )

        assert self._client is not None
        try:
            doc = self._client.get_document(key=article_id)
            return {
                "chunk": doc.get("chunk", ""),
                "title": doc.get("title", ""),
                "chunk_id": doc.get("chunk_id", ""),
                "score": 1.0,
            }
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("get_article(%s) failed: %s", article_id, exc)
            return None

    def _fallback_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Keyword substring match over the static fallback chunk list."""
        q = query.lower()
        scored = [
            (
                a,
                sum(
                    word in a["chunk"].lower() or word in a["title"].lower()
                    for word in q.split()
                ),
            )
            for a in _FALLBACK_ARTICLES
        ]
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)
        return [a for a, _ in ranked[:top_k]]

    async def health_check(self) -> ConnectorHealth:
        if not self._live:
            return ConnectorHealth(
                name="azure_search",
                connected=False,
                source="fallback",
                error="Not configured",
            )
        start = time.perf_counter()
        try:
            assert self._client is not None
            # Minimal probe — fetch zero results
            list(self._client.search(search_text="ping", top=1))
            latency = int((time.perf_counter() - start) * 1000)
            return ConnectorHealth(
                name="azure_search", connected=True, source="live", latency_ms=latency
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectorHealth(
                name="azure_search",
                connected=False,
                source="fallback",
                error=str(exc),
            )
