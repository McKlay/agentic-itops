from __future__ import annotations

"""Assistants stub — mirrors the OpenAI Assistants API surface.

Full implementation deferred until Phase 12+ when all agents are production-ready.
Returns a static list of available assistant definitions derived from the agent manifest.
"""

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser

router = APIRouter(tags=["Assistants"])

# Static manifest — will be replaced by dynamic discovery once agents stabilise
_ASSISTANTS = [
    {
        "id": "asst_supervisor",
        "name": "Supervisor",
        "description": "Intent classification and agent routing",
        "model": "gpt-4.1",
        "tools": [],
    },
    {
        "id": "asst_knowledge",
        "name": "Knowledge Agent",
        "description": "Hybrid RAG retrieval over the Azure AI Search knowledge index",
        "model": "gpt-4.1",
        "tools": ["hybrid_search", "get_article"],
    },
    {
        "id": "asst_incident",
        "name": "Incident Agent",
        "description": "ServiceNow incident triage and resolution drafting",
        "model": "gpt-4.1",
        "tools": ["lookup_incident", "create_incident", "update_incident"],
    },
    {
        "id": "asst_problem",
        "name": "Problem RCA Agent",
        "description": "Root cause analysis and corrective action planning",
        "model": "gpt-4.1",
        "tools": ["lookup_incident", "get_signals"],
    },
    {
        "id": "asst_postmortem",
        "name": "Postmortem Agent",
        "description": "Postmortem document generation and review agenda",
        "model": "gpt-4.1",
        "tools": ["lookup_incident", "get_article"],
    },
    {
        "id": "asst_governance",
        "name": "Governance Agent",
        "description": "Alert governance review and rule update drafting",
        "model": "gpt-4.1",
        "tools": ["get_metrics", "get_signals"],
    },
]


@router.get("/v1/assistants", summary="List available agent assistants")
async def list_assistants(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return metadata for all registered agent assistants."""
    return {"object": "list", "data": _ASSISTANTS, "total": len(_ASSISTANTS)}
