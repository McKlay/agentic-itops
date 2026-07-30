from __future__ import annotations

"""Shared FastAPI dependency providers for all route modules.

Usage::

    from app.routes import get_orchestrator, get_store, get_connectors

    @router.get("/example")
    async def example(
        orchestrator: Orchestrator = Depends(get_orchestrator),
        store: DomainStoreInterface = Depends(get_store),
    ): ...
"""

from fastapi import Request

from app.connectors import ConnectorBundle
from app.services.orchestrator import Orchestrator
from app.store.base import DomainStoreInterface


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_store(request: Request) -> DomainStoreInterface:
    return request.app.state.store


def get_connectors(request: Request) -> ConnectorBundle:
    return request.app.state.connectors
