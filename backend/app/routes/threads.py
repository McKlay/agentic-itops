from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.chat import MessageRecord, OperationalThread
from app.routes import get_orchestrator, get_store
from app.services.chat import ChatService
from app.services.orchestrator import Orchestrator
from app.store.base import DomainStoreInterface

router = APIRouter(tags=["Threads"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CreateThreadRequest(BaseModel):
    title: str = ""
    metadata: dict[str, Any] = {}


class RunRequest(BaseModel):
    """Body for POST /v1/threads/{id}/runs/wait."""
    message: str | None = None
    resume_decision: dict | None = None   # set when resuming after HITL


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/v1/threads", summary="Create a new conversation thread", status_code=201)
async def create_thread(
    body: CreateThreadRequest,
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> OperationalThread:
    """Create and persist a new ``OperationalThread``."""
    thread = OperationalThread(
        thread_id=f"thr_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        title=body.title or "New Conversation",
        created_at=_now(),
        updated_at=_now(),
    )
    await store.add_thread(thread)
    await store.log_event("thread_created", {"thread_id": thread.thread_id, "user_id": user.user_id})
    return thread


@router.get("/v1/threads/{thread_id}", summary="Get thread detail")
async def get_thread(
    thread_id: str,
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> OperationalThread:
    thread = await store.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Thread {thread_id!r} not found")
    return thread


@router.post("/v1/threads/{thread_id}/runs/wait", summary="Execute or resume a graph run")
async def run_thread(
    thread_id: str,
    body: RunRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Invoke the agent pipeline on a thread, or resume a paused HITL run.

    - Supply ``message`` to start a new run.
    - Supply ``resume_decision`` (with ``message=None``) to resume after HITL approval.
    """
    if body.resume_decision is not None:
        result = await orchestrator.resume(thread_id, body.resume_decision)
        return {"status": "resumed", "thread_id": thread_id, "state": result}

    if not body.message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'message' or 'resume_decision' must be provided",
        )

    service = ChatService(orchestrator, store)
    response = await service.handle(body.message, thread_id, user)
    return {"status": "completed", "thread_id": thread_id, "response": response.model_dump()}


@router.get("/v1/threads/{thread_id}/state", summary="Inspect current LangGraph checkpoint state")
async def get_thread_state(
    thread_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return the latest LangGraph checkpoint values for *thread_id*."""
    return await orchestrator.get_thread_state(thread_id)


@router.get("/v1/threads/{thread_id}/history", summary="Get conversation message history")
async def get_thread_history(
    thread_id: str,
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> list[MessageRecord]:
    """Return all stored ``MessageRecord`` objects for the thread."""
    return await store.get_messages(thread_id)
