from __future__ import annotations

"""Phase 12 — Knowledge Agent End-to-End Integration Tests.

These tests exercise the full HTTP pipeline (FastAPI app → orchestrator →
supervisor → knowledge_agent → critic → response_formatter) with mocked
LLM responses.  They validate checklist items 12.1–12.7.

All results use the live ka-vector index schema:
    chunk, title, chunk_id, score
"""

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.connectors.azure_openai import AzureOpenAIConnector
from app.connectors.azure_search import AzureSearchConnector
from app.models.agent import AgentOutput, RunContext
from app.services.orchestrator import Orchestrator
from app.store.memory import InMemoryStore
from app.connectors import build_connectors
from app.agents.critic import CriticAgent
from langchain_core.messages import HumanMessage

_KNOWLEDGE_QUERY = "How do I troubleshoot SAP SSO login failures?"


# ---------------------------------------------------------------------------
# Mock LLM response builders
# ---------------------------------------------------------------------------

def _text_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = []
    msg.role = "assistant"
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _tool_call_response(name: str, args: dict[str, Any], call_id: str = "call_abc") -> MagicMock:
    fn = MagicMock()
    fn.name = name
    fn.arguments = json.dumps(args)
    tc = MagicMock()
    tc.id = call_id
    tc.function = fn
    tc.type = "function"
    msg = MagicMock()
    msg.content = ""
    msg.tool_calls = [tc]
    msg.role = "assistant"
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "tool_calls"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# Ordered pipeline responses: supervisor → knowledge(tool_call) → knowledge(synthesis) → critic
_SUPERVISOR_RESP = _text_response(json.dumps({
    "intent": "search_knowledge",
    "agents": ["knowledge_agent"],
    "requires_approval": False,
    "rationale": "Knowledge retrieval query.",
}))

_KNOWLEDGE_TOOL_RESP = _tool_call_response(
    "hybrid_search",
    {"query": "SAP SSO login failures troubleshooting", "top_k": 5},
)

_KNOWLEDGE_SYNTH_RESP = _text_response(json.dumps({
    "summary": (
        "SAP SSO login failures are commonly caused by SAML assertion errors, "
        "certificate expiry, or AD trust issues. See KB0001001.pdf."
    ),
    "detail": (
        "Step 1: Check IdP certificate on ADFS console. "
        "Step 2: Verify SP metadata in SAP SICF. "
        "Step 3: Review SAML trace in browser dev tools. "
        "See [KB0001001.pdf](ka_0001_chunk_0) for the full procedure."
    ),
    "citations": ["KB0001001.pdf — SAP Single Sign-On Troubleshooting Guide"],
    "gap_detected": False,
    "confidence": 0.92,
}))

_CRITIC_RESP = _text_response(json.dumps({
    "score": 0.88,
    "accuracy": 0.90, "completeness": 0.85, "clarity": 0.92, "safety": 0.85,
    "feedback": "Well-cited answer grounded in KB article chunks.",
}))

_FULL_PIPELINE = [_SUPERVISOR_RESP, _KNOWLEDGE_TOOL_RESP, _KNOWLEDGE_SYNTH_RESP, _CRITIC_RESP]


# ---------------------------------------------------------------------------
# 12.5 — ChatResponse includes message text + agent_outputs (full HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_12_5_chat_response_structure(async_client) -> None:
    """POST /api/chat returns ChatResponse with message text + agent_outputs."""
    from unittest.mock import patch

    with patch(
        "app.connectors.azure_openai.AzureOpenAIConnector.chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.side_effect = list(_FULL_PIPELINE)
        response = await async_client.post("/api/chat", json={"message": _KNOWLEDGE_QUERY})

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "thread_id" in data
    assert isinstance(data["message"], str) and data["message"]
    assert isinstance(data["agent_outputs"], list) and len(data["agent_outputs"]) >= 1
    assert "timestamp" in data

    # Verify agent_outputs structure has the correct agent_id
    out = data["agent_outputs"][-1]
    assert out["agent_id"] == "knowledge_agent"
    assert out["requires_approval"] is False


# ---------------------------------------------------------------------------
# 12.6 — MessageRecords persisted in domain store for thread history (full HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_12_6_message_records_persisted(async_client) -> None:
    """After POST /api/chat, both user and assistant MessageRecords are in the store."""
    from unittest.mock import patch

    thread_id = f"thr_{uuid.uuid4().hex[:12]}"

    with patch(
        "app.connectors.azure_openai.AzureOpenAIConnector.chat_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.side_effect = list(_FULL_PIPELINE)
        response = await async_client.post(
            "/api/chat",
            json={"message": _KNOWLEDGE_QUERY, "thread_id": thread_id},
        )

    assert response.status_code == 200

    history_response = await async_client.get(f"/v1/threads/{thread_id}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    roles = [msg["role"] for msg in history]
    assert "user" in roles, f"User message not persisted. History: {history}"
    assert "assistant" in roles, f"Assistant message not persisted. History: {history}"


# ---------------------------------------------------------------------------
# 12.7 — Critic routes passing output to response_formatter (unit-level)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_12_7_critic_passes_and_routes_to_formatter() -> None:
    """CriticAgent returns score ≥ 0.7 → orchestrator routes to response_formatter."""
    settings = Settings(auth_disabled=True, storage_backend="memory")
    llm = AzureOpenAIConnector(settings)
    llm._live = False
    llm._client = None

    critic = CriticAgent(llm=llm)

    sample = AgentOutput(
        output_id="out_12_7",
        agent_id="knowledge_agent",
        intent="search_knowledge",
        summary="SAP SSO failures. See KB0001001.pdf.",
        detail="Step 1: Check IdP cert.",
        citations=["KB0001001.pdf — SAP SSO Troubleshooting"],
        requires_approval=False,
        confidence=0.92,
    )
    state = RunContext(
        thread_id="thr_12_7",
        intent="search_knowledge",
        agent_outputs=[sample],
        messages=[HumanMessage(content=_KNOWLEDGE_QUERY)],
    )

    llm.chat_completion = AsyncMock(return_value=_CRITIC_RESP)
    result = await critic.run(state)

    score = result["critic_score"]
    assert score >= 0.7

    # Verify routing logic
    connectors = build_connectors(settings, InMemoryStore())
    orch = Orchestrator(settings, connectors, InMemoryStore())
    final_state = RunContext(critic_score=score, requires_approval=False, retry_count=0)
    route = orch._route_critic(final_state)
    assert route == "response_formatter"
