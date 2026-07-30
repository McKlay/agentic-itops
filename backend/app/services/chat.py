from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.agent import AgentOutput
from app.models.approval import ApprovalTask
from app.models.auth import CurrentUser
from app.models.chat import ChatResponse, MessageRecord
from app.services.orchestrator import Orchestrator
from app.store.base import DomainStoreInterface

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _msg_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


class ChatService:
    """Handle user messages: persist records, drive orchestrator, return response.

    Processing flow (per SVC §3.3):
    1. Persist user ``MessageRecord`` in domain store
    2. Invoke ``Orchestrator.run()`` → LangGraph pipeline
    3. Extract ``agent_outputs`` and ``pending_approvals`` from final state
    4. Persist assistant ``MessageRecord`` in domain store
    5. Return typed ``ChatResponse``
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        store: DomainStoreInterface,
    ) -> None:
        self._orchestrator = orchestrator
        self._store = store

    async def handle(
        self,
        message: str,
        thread_id: str,
        user: CurrentUser,
    ) -> ChatResponse:
        """Process a user message through the full agent pipeline."""
        logger.info(
            "[chat] Received message thread=%s user=%s message=%r",
            thread_id, user.email, message[:120],
        )
        # 1. Persist user message
        user_msg = MessageRecord(
            message_id=_msg_id(),
            thread_id=thread_id,
            role="user",
            content=message,
            created_at=_now(),
        )
        await self._store.add_message(user_msg)

        user_dict = {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "roles": list(user.roles),
        }

        # 2. Invoke orchestrator
        logger.info("[chat] Invoking orchestrator thread=%s", thread_id)
        try:
            final_state = await self._orchestrator.run(message, thread_id, user_dict)
            logger.info("[chat] Orchestrator completed thread=%s", thread_id)
        except Exception:
            logger.exception("Orchestrator run failed for thread %s", thread_id)
            final_state = {}

        # 3. Extract outputs
        agent_outputs: list[AgentOutput] = list(
            final_state.get("agent_outputs") or []
        )
        reply_text: str = (
            final_state.get("final_response")
            or (agent_outputs[-1].summary if agent_outputs else "")
            or "I encountered an issue processing your request. Please try again."
        )

        # Collect pending approvals from outputs that require human sign-off
        pending_approvals: list[ApprovalTask] = []
        for output in agent_outputs:
            if output.requires_approval and output.status == "pending":
                task = ApprovalTask(
                    task_id=f"apr_{uuid.uuid4().hex[:12]}",
                    output_id=output.output_id,
                    thread_id=thread_id,
                    agent_id=output.agent_id,
                    summary=output.summary,
                    created_at=_now(),
                )
                pending_approvals.append(task)
                await self._store.add_approval(task)

        # 4. Persist assistant message
        asst_msg = MessageRecord(
            message_id=_msg_id(),
            thread_id=thread_id,
            role="assistant",
            content=reply_text,
            created_at=_now(),
        )
        await self._store.add_message(asst_msg)

        logger.info(
            "[chat] Responding thread=%s agent_outputs=%d pending_approvals=%d reply=%r",
            thread_id,
            len(agent_outputs),
            len(pending_approvals),
            reply_text[:120],
        )
        # 5. Return response
        return ChatResponse(
            thread_id=thread_id,
            message=reply_text,
            agent_outputs=agent_outputs,
            pending_approvals=pending_approvals,
            timestamp=_now(),
        )

    async def get_history(self, thread_id: str) -> list[MessageRecord]:
        """Return conversation history for a thread (most recent 20 messages)."""
        messages = await self._store.get_messages(thread_id)
        return messages[-20:]
