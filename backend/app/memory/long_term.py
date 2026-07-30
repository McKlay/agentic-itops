from __future__ import annotations

from langgraph.store.base import BaseStore  # type: ignore[import]


class LongTermMemoryStore(BaseStore):
    """Cross-session long-term memory store — interface placeholder.

    NOT instantiated in POC.  Defined here for architectural completeness and
    to reserve the import path used by the Orchestrator when LTM is enabled.

    Production implementation will use Azure Cosmos DB (MongoDB API) with
    TTL-based expiration, enabling:

    - **User preference learning** — resolution style, notification preferences
    - **Resolution pattern caching** — embedding-indexed past resolutions
    - **KB quality scoring** — track which articles lead to successful resolutions
    - **Agent tuning** — per-agent performance baselines, adaptive critic thresholds

    Activation:
    1. Provision Azure Cosmos DB (MongoDB API) or compatible vector store.
    2. Implement ``aget``, ``aput``, ``adelete``, ``abatch`` using Motor driver.
    3. Pass instance to ``graph.compile(store=ltm_store)`` in the Orchestrator.
    """

    async def aget(self, key: str, namespace: tuple | None = None) -> object:  # type: ignore[override]
        raise NotImplementedError("LongTermMemoryStore is not implemented in POC.")

    async def aput(  # type: ignore[override]
        self, key: str, value: object, namespace: tuple | None = None
    ) -> None:
        raise NotImplementedError("LongTermMemoryStore is not implemented in POC.")

    async def adelete(self, key: str, namespace: tuple | None = None) -> None:  # type: ignore[override]
        raise NotImplementedError("LongTermMemoryStore is not implemented in POC.")

    async def abatch(self, ops: list) -> list:  # type: ignore[override]
        raise NotImplementedError("LongTermMemoryStore is not implemented in POC.")

    def batch(self, ops: list) -> list:  # type: ignore[override]
        raise NotImplementedError("LongTermMemoryStore is not implemented in POC.")
