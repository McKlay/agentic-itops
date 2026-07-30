from __future__ import annotations

"""Approval service — lifecycle management for agent-generated approval tasks.

Lifecycle: create → review → dispatch
  1. ``ApprovalTask`` created by ChatService when ``AgentOutput.requires_approval=True``
  2. Human reviewer submits ``ApprovalDecision`` via ``POST /api/approvals/{id}/decision``
  3. ``dispatch_approved_output()`` sends approved action to ServiceNow (deferred)

Activation note: Full ServiceNow dispatch is deferred until Phase 10+ (routes wired).
Until then, approval records are persisted in domain store for audit purposes only.
"""

import logging
from datetime import UTC, datetime

from app.models.approval import ApprovalDecision, ApprovalTask
from app.store.base import DomainStoreInterface

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ApprovalService:
    """Manage HITL approval lifecycle: create, review, dispatch.

    All state-changing operations are logged to the domain store audit log.
    """

    def __init__(self, store: DomainStoreInterface) -> None:
        self._store = store

    async def get_pending(self, thread_id: str | None = None) -> list[ApprovalTask]:
        """Return all approvals with ``status="pending"``, optionally filtered by thread."""
        pending = await self._store.list_approvals(status="pending")
        if thread_id:
            pending = [a for a in pending if a.thread_id == thread_id]
        return pending

    async def apply_decision(
        self,
        task_id: str,
        decision: ApprovalDecision,
    ) -> ApprovalTask:
        """Record an approval or rejection decision.

        Args:
            task_id: The ``apr_*`` task_id of the approval to decide on.
            decision: ``ApprovalDecision`` carrying ``decision`` + ``reviewer``.

        Returns:
            Updated ``ApprovalTask`` retrieved from the store after the write.

        Raises:
            KeyError: If no approval with ``task_id`` exists.
        """
        # Locate the task — list and filter (no get_approval in interface)
        all_pending = await self._store.list_approvals()
        matching = [a for a in all_pending if a.task_id == task_id]
        if not matching:
            raise KeyError(f"Approval {task_id!r} not found")

        await self._store.update_approval(task_id, decision)

        await self._store.log_event(
            "approval_decision",
            {
                "task_id": task_id,
                "decision": decision.decision,
                "reviewer": decision.reviewer,
            },
        )

        if decision.decision == "approved":
            task = matching[0]
            await self._dispatch_approved_output(task)

        # Return the latest state of the task
        updated = [a for a in await self._store.list_approvals() if a.task_id == task_id]
        return updated[0] if updated else matching[0]

    async def _dispatch_approved_output(self, task: ApprovalTask) -> None:
        """Push approved action to ServiceNow.

        TODO (Phase 10+): Retrieve the linked ``AgentOutput``, call the
        ServiceNow connector with the proposed changes, and log the result.
        Until that wiring exists this is a no-op audit entry.
        """
        logger.info(
            "Approval %s approved — ServiceNow dispatch deferred (Phase 10+)",
            task.task_id,
        )
        await self._store.log_event(
            "approval_dispatch_deferred",
            {"task_id": task.task_id, "output_id": task.output_id},
        )
