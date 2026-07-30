from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.agent import AgentOutput
from app.models.approval import ApprovalTask


class OperationalThread(BaseModel):
    """Conversation thread metadata persisted in the Domain Store."""

    thread_id: str                                     # thr_ prefix
    user_id: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    message_count: int = 0
    last_intent: str = ""


class MessageRecord(BaseModel):
    """Individual message stored in the Domain Store for a thread."""

    message_id: str                                    # msg_ prefix
    thread_id: str
    role: str                                          # user | assistant | system
    content: str
    created_at: str = ""
    agent_id: str | None = None                        # set when role == assistant


class ChatRequest(BaseModel):
    """Incoming chat request body sent by the frontend."""

    message: str
    thread_id: str | None = None                       # None → create new thread


class ChatResponse(BaseModel):
    """Outgoing chat response returned to the frontend."""

    thread_id: str
    message: str
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    pending_approvals: list[ApprovalTask] = Field(default_factory=list)
    timestamp: str
