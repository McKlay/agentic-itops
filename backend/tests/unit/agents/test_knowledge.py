from __future__ import annotations

"""Unit tests — KnowledgeAgent RAG retrieval loop.

Validates the ReAct loop, tool invocation, output parsing, and gap detection
using the ka-vector index schema (chunk, title, chunk_id, score).
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.agents.knowledge import KnowledgeAgent
from app.config import Settings
from app.connectors.azure_openai import AzureOpenAIConnector
from app.connectors.azure_search import AzureSearchConnector
from app.models.agent import AgentOutput, RunContext
from app.tools.registry import ToolRegistry
from app.tools.schemas import ALL_SCHEMAS
from app.tools.search_tools import make_search_tools

_QUERY = "How do I troubleshoot SAP SSO login failures?"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def llm() -> AzureOpenAIConnector:
    conn = AzureOpenAIConnector(Settings(auth_disabled=True, storage_backend="memory"))
    conn._live = False
    conn._client = None
    return conn


@pytest.fixture()
def search() -> AzureSearchConnector:
    conn = AzureSearchConnector(Settings(auth_disabled=True, storage_backend="memory"))
    conn._live = False
    conn._client = None
    return conn


@pytest.fixture()
def registry(search: AzureSearchConnector, llm: AzureOpenAIConnector) -> ToolRegistry:
    reg = ToolRegistry()
    hs, ga = make_search_tools(search, llm)
    reg.register("hybrid_search", hs, ALL_SCHEMAS["hybrid_search"])
    reg.register("get_article", ga, ALL_SCHEMAS["get_article"])
    return reg


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------

def _text_resp(content: str) -> MagicMock:
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


def _tool_call_resp(name: str, args: dict[str, Any], call_id: str = "call_1") -> MagicMock:
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


_SYNTHESIS = json.dumps({
    "summary": "SAP SSO failures are caused by SAML assertions or certificate expiry. See KB0001001.pdf.",
    "detail": "Step 1: Check IdP cert. Step 2: Verify SP metadata.",
    "citations": ["KB0001001.pdf — SAP SSO Troubleshooting"],
    "gap_detected": False,
    "confidence": 0.92,
})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_knowledge_agent_calls_hybrid_search(llm: AzureOpenAIConnector, registry: ToolRegistry) -> None:
    """KnowledgeAgent invokes hybrid_search and returns tool_results with new schema fields."""
    agent = KnowledgeAgent(llm=llm, tool_registry=registry)
    state = RunContext(thread_id="thr_k01", intent="search_knowledge", messages=[HumanMessage(content=_QUERY)])

    llm.chat_completion = AsyncMock(side_effect=[
        _tool_call_resp("hybrid_search", {"query": "SAP SSO", "top_k": 5}),
        _text_resp(_SYNTHESIS),
    ])
    result = await agent.run(state)

    tool_results = result.get("tool_results", [])
    hs_calls = [t for t in tool_results if t.tool_name == "hybrid_search"]
    assert hs_calls, "hybrid_search was not invoked"

    # The fallback results use the new schema — verify by checking the result content
    first_result = hs_calls[0].result
    assert isinstance(first_result, list)
    if first_result:
        assert "chunk" in first_result[0], f"Expected 'chunk' key, got {first_result[0].keys()}"
        assert "title" in first_result[0]
        assert "chunk_id" in first_result[0]


@pytest.mark.asyncio
async def test_knowledge_agent_output_no_approval(llm: AzureOpenAIConnector, registry: ToolRegistry) -> None:
    """KnowledgeAgent output has requires_approval=False and non-empty summary."""
    agent = KnowledgeAgent(llm=llm, tool_registry=registry)
    state = RunContext(thread_id="thr_k02", intent="search_knowledge", messages=[HumanMessage(content=_QUERY)])

    llm.chat_completion = AsyncMock(side_effect=[
        _tool_call_resp("hybrid_search", {"query": "SAP SSO", "top_k": 5}),
        _text_resp(_SYNTHESIS),
    ])
    result = await agent.run(state)

    outputs: list[AgentOutput] = result.get("agent_outputs", [])
    assert outputs
    out = outputs[-1]
    assert out.requires_approval is False
    assert out.agent_id == "knowledge_agent"
    assert out.summary
    assert out.confidence > 0.0


@pytest.mark.asyncio
async def test_knowledge_agent_gap_detection(llm: AzureOpenAIConnector, registry: ToolRegistry) -> None:
    """KnowledgeAgent detects a knowledge gap when no articles match."""
    agent = KnowledgeAgent(llm=llm, tool_registry=registry)
    state = RunContext(thread_id="thr_k03", intent="search_knowledge", messages=[HumanMessage(content=_QUERY)])

    gap_resp = json.dumps({
        "summary": "No articles found.",
        "detail": "Knowledge gap detected.",
        "citations": [],
        "gap_detected": True,
        "confidence": 0.3,
    })
    llm.chat_completion = AsyncMock(side_effect=[
        _tool_call_resp("hybrid_search", {"query": "SAP SSO", "top_k": 5}),
        _text_resp(gap_resp),
    ])
    result = await agent.run(state)

    outputs: list[AgentOutput] = result.get("agent_outputs", [])
    assert outputs
    out = outputs[-1]
    assert "knowledge gap" in out.summary.lower()
    assert out.confidence == 0.5  # gap forces confidence to 0.5
