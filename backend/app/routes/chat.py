from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.chat import ChatRequest, ChatResponse
from app.routes import get_orchestrator, get_store
from app.services.chat import ChatService
from app.services.orchestrator import Orchestrator
from app.store.base import DomainStoreInterface

router = APIRouter(tags=["Chat"])


@router.post("/api/chat", summary="Process a user message through the agent pipeline")
async def chat(
    body: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    """Accept a user message and return the agent-generated response.

    - Creates a new thread automatically if ``thread_id`` is ``None``.
    - Runs the full Supervisor → Agent → Critic → (HITL) → Formatter pipeline.
    - Returns ``pending_approvals`` when an agent action requires human sign-off.
    """
    # Auto-generate thread_id if not provided
    thread_id = body.thread_id or f"thr_{uuid.uuid4().hex[:12]}"
    service = ChatService(orchestrator, store)
    return await service.handle(body.message, thread_id, user)
