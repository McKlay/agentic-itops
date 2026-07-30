from __future__ import annotations

"""Unit tests — CriticAgent quality scoring."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.agents.critic import CriticAgent
from app.config import Settings
from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import AgentOutput, RunContext


def _mock_llm() -> AzureOpenAIConnector:
    llm = AzureOpenAIConnector(Settings(auth_disabled=True, storage_backend="memory"))
    llm._live = False
    llm._client = None
    return llm


def _text_resp(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = []
    msg.role = "assistant"
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


_SAMPLE_OUTPUT = AgentOutput(
    output_id="out_c01",
    agent_id="knowledge_agent",
    intent="search_knowledge",
    summary="SAP SSO failures are caused by SAML issues. See KB0001001.pdf.",
    detail="Step 1: Check IdP cert. Step 2: Verify SP metadata.",
    citations=["KB0001001.pdf — SAP SSO Troubleshooting"],
    requires_approval=False,
    confidence=0.92,
)


@pytest.mark.asyncio
async def test_critic_passes_high_quality_output() -> None:
    """Critic returns score ≥ 0.7 for a well-cited answer."""
    llm = _mock_llm()
    critic = CriticAgent(llm=llm)
    state = RunContext(
        thread_id="thr_c01",
        agent_outputs=[_SAMPLE_OUTPUT],
        messages=[HumanMessage(content="test")],
    )
    llm.chat_completion = AsyncMock(return_value=_text_resp(json.dumps({
        "score": 0.88, "accuracy": 0.90, "completeness": 0.85,
        "clarity": 0.92, "safety": 0.85,
        "feedback": "Well-cited answer.",
    })))
    result = await critic.run(state)
    assert result["critic_score"] >= 0.7
    assert result["retry_count"] == 0  # no retry for passing score


@pytest.mark.asyncio
async def test_critic_fails_low_quality_output() -> None:
    """Critic increments retry_count when score < 0.7."""
    llm = _mock_llm()
    critic = CriticAgent(llm=llm)
    state = RunContext(
        thread_id="thr_c02",
        agent_outputs=[_SAMPLE_OUTPUT],
        messages=[HumanMessage(content="test")],
        retry_count=0,
    )
    llm.chat_completion = AsyncMock(return_value=_text_resp(json.dumps({
        "score": 0.45, "feedback": "Answer lacks citations.",
    })))
    result = await critic.run(state)
    assert result["critic_score"] < 0.7
    assert result["retry_count"] == 1


@pytest.mark.asyncio
async def test_critic_no_outputs_passes() -> None:
    """Critic passes through with score 1.0 when agent_outputs is empty."""
    llm = _mock_llm()
    critic = CriticAgent(llm=llm)
    state = RunContext(thread_id="thr_c03", agent_outputs=[], messages=[HumanMessage(content="test")])
    result = await critic.run(state)
    assert result["critic_score"] == 1.0
