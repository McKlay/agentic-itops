from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth import get_current_user
from app.models.approval import ApprovalDecision, ApprovalTask
from app.models.auth import CurrentUser
from app.routes import get_orchestrator, get_store
from app.services.approval import ApprovalService
from app.services.orchestrator import Orchestrator
from app.store.base import DomainStoreInterface

router = APIRouter(tags=["Approvals"])


@router.get("/api/approvals", summary="List pending approvals")
async def list_approvals(
    thread_id: str | None = None,
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> list[ApprovalTask]:
    """Return pending ``ApprovalTask`` records, optionally filtered by thread."""
    service = ApprovalService(store)
    return await service.get_pending(thread_id=thread_id)


@router.post("/api/approvals/{task_id}/decision", summary="Submit approval or rejection decision")
async def submit_decision(
    task_id: str,
    body: ApprovalDecision,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Record an approval or rejection and optionally resume the paused graph run.

    - ``decision: "approved"`` → updates the store, resumes the LangGraph run
    - ``decision: "rejected"`` → updates the store, does not resume the graph
    """
    # Override reviewer with the authenticated user
    body = body.model_copy(update={"reviewer": user.email or user.user_id})

    service = ApprovalService(store)
    try:
        task = await service.apply_decision(task_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if body.decision == "approved":
        # Resume the paused LangGraph run for this thread
        thread_id = task.thread_id
        try:
            result = await orchestrator.resume(thread_id, body.model_dump())
            return {"status": "approved_and_resumed", "task_id": task_id, "thread_id": thread_id, "result": result}
        except Exception:
            # Graph may already be completed or not resumable — return approval status only
            return {"status": "approved", "task_id": task_id, "thread_id": thread_id}

    return {"status": "rejected", "task_id": task_id}
