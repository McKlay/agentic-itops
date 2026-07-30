from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel


class ConnectorHealth(BaseModel):
    """Health check result returned by every connector."""

    name: str = ""
    connected: bool = False
    source: str = "fallback"          # "live" | "fallback"
    latency_ms: int | None = None
    error: str | None = None


class ConnectorBase(ABC):
    """Abstract base class for all external service connectors.

    Every concrete connector must:
    - Set ``self._live = True`` in ``__init__`` when all required env vars are present.
    - Implement ``health_check()`` — called by ``GET /healthz``.
    - Call ``self._require_live(operation)`` before any outbound call and short-circuit
      to the in-memory fallback when it returns ``False``.
    """

    def __init__(self, settings: object) -> None:
        self._live: bool = False
        self._settings = settings
        self.logger = logging.getLogger(f"connectors.{self.__class__.__name__}")

    @abstractmethod
    async def health_check(self) -> ConnectorHealth: ...

    def _require_live(self, operation: str) -> bool:
        """Log a warning and return False when the connector is not live."""
        if not self._live:
            self.logger.warning(
                "Connector offline — using fallback for '%s'", operation
            )
        return self._live
