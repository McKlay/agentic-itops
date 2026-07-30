from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger(__name__)


async def create_domain_store(settings: Settings):  # -> DomainStoreInterface
    """Factory that returns the correct store implementation based on ``STORAGE_BACKEND``.

    Priority:
    1. ``cosmos``       — Azure Cosmos DB (MongoDB API)  [UAT / Production]
    2. ``azure_table``  — Azure Table Storage             [Cost-optimised alternative]
    3. ``memory``       — In-memory dict store (default)  [POC / local dev]
    """
    from app.store.base import DomainStoreInterface  # noqa: F401 (re-exported)

    backend = (settings.storage_backend or "memory").lower()

    if backend == "cosmos":
        from app.store.cosmos import CosmosStore
        store = CosmosStore(settings.cosmos_connection_string, settings.cosmos_database)
        await store.initialize()
        logger.info("DomainStore: CosmosStore (Azure Cosmos DB)")
        return store

    if backend == "azure_table":
        from app.store.table import TableStore
        store = TableStore(settings.azure_table_connection_string)
        await store.initialize()
        logger.info("DomainStore: TableStore (Azure Table Storage)")
        return store

    from app.store.memory import InMemoryStore
    store = InMemoryStore()
    await store.seed()
    logger.info("DomainStore: InMemoryStore (seeded — POC mode)")
    return store
