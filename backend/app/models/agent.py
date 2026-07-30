from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.models.auth import CurrentUser


class ToolCallResult(BaseModel):
    """Result of a single tool execution within an agent's ReAct loop."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class AgentOutput(BaseModel):
    """Structured output produced by an agent after its reasoning loop completes."""

    output_id: str                                     # out_ prefix
    agent_id: str
    intent: str = ""
    summary: str = ""                                  # quick 1-2 sentence answer (shown in chat bubble)
    detail: str = ""                                   # fallback prose detail (legacy / non-procedural)
    steps: list[str] = Field(default_factory=list)     # numbered procedure steps (shown in artifact card)
    notes: list[str] = Field(default_factory=list)     # key caveats / warnings
    citations: list[str] = Field(default_factory=list)
    citation_urls: dict[str, str] = Field(default_factory=dict)  # citation string → blob storage PDF URL
    tool_calls: list[ToolCallResult] = Field(default_factory=list)
    requires_approval: bool = False
    status: str = "pending"                            # pending | approved | rejected
    confidence: float = 1.0
    created_at: str = ""
    target_id: str | None = None                       # linked incident / problem / change ID


class RunContext(BaseModel):
    """Working memory — shared state within a single LangGraph graph execution.

    This is the LangGraph state schema (Tier 2).  Every node reads from and writes
    to this object.  It is NOT persisted beyond the run — durable artifacts are
    extracted to the Domain Store by the response_formatter node.

    The ``messages`` field uses the ``add_messages`` reducer so that returning
    ``{"messages": [new_msg]}`` from any node *appends* to the list rather than
    replacing it, giving every downstream node the full conversation history in
    native OpenAI message format.
    """

    # Thread identity
    thread_id: str = ""
    user: CurrentUser | None = None

    # Supervisor classification
    intent: str = ""
    selected_agents: list[str] = Field(default_factory=list)
    requires_approval: bool = False

    # Message accumulation — OpenAI format (LangGraph add_messages reducer)
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)

    # Agent pipeline state
    target_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    tool_results: list[ToolCallResult] = Field(default_factory=list)

    # Quality gate
    retry_count: int = 0
    max_retries: int = 2
    critic_score: float | None = None
    critic_feedback: str = ""

    # Approval gate
    approval_decision: dict[str, Any] | None = None

    # General chat fallback reply (set by general_chat_agent node)
    general_chat_reply: str = ""

    # Final assembled reply from response_formatter (written to state for chat.py)
    final_response: str = ""
