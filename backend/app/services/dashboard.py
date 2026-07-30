from __future__ import annotations

"""Dashboard service — aggregate incident and knowledge metrics for the frontend.

The domain store's ``snapshot()`` method already performs the heavy aggregation.
``DashboardService`` acts as the service-layer wrapper: it can enrich the snapshot
with additional computed fields in future phases (e.g. MTTR trends, SLA burn-down)
without changing the route handler contract.

Activation note: Time-series metrics (MTTR, SLA burn-down, trending) require
Application Insights / telemetry connector — deferred to Phase 12+.
"""

import logging

from app.models.dashboard import DashboardSnapshot
from app.store.base import DomainStoreInterface

logger = logging.getLogger(__name__)


class DashboardService:
    """Aggregate operational metrics for the Command Center dashboard."""

    def __init__(self, store: DomainStoreInterface) -> None:
        self._store = store

    async def snapshot(self) -> DashboardSnapshot:
        """Return a point-in-time ``DashboardSnapshot``.

        Delegates to ``DomainStoreInterface.snapshot()`` which aggregates
        incidents, approvals, threads, and knowledge article counts.
        Additional enrichment (trends, time-series) will be added here
        when telemetry connectors are available (Phase 12+).
        """
        snap = await self._store.snapshot()
        logger.debug(
            "Dashboard snapshot: open=%d p1=%d pending_approvals=%d",
            snap.open_incidents,
            snap.p1_incidents,
            snap.pending_approvals,
        )
        return snap
