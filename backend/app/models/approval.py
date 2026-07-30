from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApprovalTask(BaseModel):
    """HITL approval lifecycle object.

    Created by the hitl_gate node when an AgentOutput requires human sign-off.
    Status transitions: pending → approved | rejected.
    """

    task_id: str                                       # apr_ prefix
    output_id: str                                     # references AgentOutput.output_id
    thread_id: str
    agent_id: str
    intent: str = ""
    summary: str = ""
    detail: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)  # action details (e.g. SNOW fields)
    status: str = "pending"                            # pending | approved | rejected
    created_at: str = ""
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    reviewer_comment: str = ""


class ApprovalDecision(BaseModel):
    """Human approval or rejection submitted via the /api/approvals/{id}/decision endpoint."""

    decision: str                                      # approved | rejected
    reviewer: str                                      # email or user_id
    comment: str = ""
