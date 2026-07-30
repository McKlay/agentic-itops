from __future__ import annotations

"""Unit tests — SupervisorAgent intent classification.

Validates that the supervisor correctly routes knowledge queries, incident
queries, and general chat to the proper executor agent.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.agents.supervisor import SupervisorAgent
from app.connectors.azure_openai import AzureOpenAIConnector
from app.config import Settings
from app.models.agent import RunContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_llm() -> AzureOpenAIConnector:
    llm = AzureOpenAIConnector(Settings(auth_disabled=True, storage_backend="memory"))
    llm._live = False
    llm._client = None
    return llm


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_supervisor_routes_knowledge_query() -> None:
    """Supervisor classifies a KB question as search_knowledge → knowledge_agent."""
    llm = _mock_llm()
    agent = SupervisorAgent(llm=llm)
    state = RunContext(
        thread_id="thr_u01",
        messages=[HumanMessage(content="How do I troubleshoot SAP SSO login failures?")],
    )
    llm.chat_completion = AsyncMock(return_value=_text_response(json.dumps({
        "intent": "search_knowledge",
        "agents": ["knowledge_agent"],
        "requires_approval": False,
        "rationale": "Knowledge question.",
    })))
    result = await agent.run(state)

    assert result["intent"] == "search_knowledge"
    assert "knowledge_agent" in result["selected_agents"]
    assert result["requires_approval"] is False


@pytest.mark.asyncio
async def test_supervisor_routes_incident_query() -> None:
    """Supervisor classifies an incident report as triage_incident → incident_agent."""
    llm = _mock_llm()
    agent = SupervisorAgent(llm=llm)
    state = RunContext(
        thread_id="thr_u02",
        messages=[HumanMessage(content="SAP HR portal is down for all EMEA users")],
    )
    llm.chat_completion = AsyncMock(return_value=_text_response(json.dumps({
        "intent": "triage_incident",
        "agents": ["incident_agent"],
        "requires_approval": True,
        "rationale": "Active outage.",
    })))
    result = await agent.run(state)

    assert result["intent"] == "triage_incident"
    assert "incident_agent" in result["selected_agents"]
    assert result["requires_approval"] is True


@pytest.mark.asyncio
async def test_supervisor_defaults_on_invalid_json() -> None:
    """Supervisor falls back to general_chat when LLM returns invalid JSON."""
    llm = _mock_llm()
    agent = SupervisorAgent(llm=llm)
    state = RunContext(
        thread_id="thr_u03",
        messages=[HumanMessage(content="Hello!")],
    )
    llm.chat_completion = AsyncMock(return_value=_text_response("Not valid JSON at all!"))
    result = await agent.run(state)

    assert result["intent"] == "general_chat"
    assert result["selected_agents"] == []
    assert result["requires_approval"] is False
