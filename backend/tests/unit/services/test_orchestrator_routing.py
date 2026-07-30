from __future__ import annotations

"""Unit tests — Orchestrator routing logic.

Tests the _route_to_agent and _route_critic conditional edge functions
without compiling or executing the full LangGraph.
"""

import pytest

from app.config import Settings
from app.connectors import build_connectors
from app.models.agent import RunContext
from app.services.orchestrator import Orchestrator
from app.store.memory import InMemoryStore


@pytest.fixture()
def orchestrator() -> Orchestrator:
    settings = Settings(auth_disabled=True, storage_backend="memory")
    store = InMemoryStore()
    connectors = build_connectors(settings, store)
    return Orchestrator(settings, connectors, store)


def test_route_to_knowledge_agent(orchestrator: Orchestrator) -> None:
    state = RunContext(selected_agents=["knowledge_agent"])
    assert orchestrator._route_to_agent(state) == "knowledge_agent"


def test_route_to_incident_agent(orchestrator: Orchestrator) -> None:
    state = RunContext(selected_agents=["incident_agent"])
    assert orchestrator._route_to_agent(state) == "incident_agent"


def test_route_to_formatter_when_empty(orchestrator: Orchestrator) -> None:
    """No selected_agents → skip to response_formatter."""
    state = RunContext(selected_agents=[])
    assert orchestrator._route_to_agent(state) == "response_formatter"


def test_critic_passes_to_formatter(orchestrator: Orchestrator) -> None:
    """Score ≥ 0.7 and no approval → response_formatter."""
    state = RunContext(critic_score=0.85, requires_approval=False, retry_count=0)
    assert orchestrator._route_critic(state) == "response_formatter"


def test_critic_passes_to_hitl(orchestrator: Orchestrator) -> None:
    """Score ≥ 0.7 but approval required → hitl_gate."""
    state = RunContext(critic_score=0.85, requires_approval=True, retry_count=0)
    assert orchestrator._route_critic(state) == "hitl_gate"


def test_critic_retries_on_low_score(orchestrator: Orchestrator) -> None:
    """Score < 0.7 with retries left → back to supervisor."""
    state = RunContext(critic_score=0.4, requires_approval=False, retry_count=0)
    assert orchestrator._route_critic(state) == "supervisor"


def test_critic_escalates_after_max_retries(orchestrator: Orchestrator) -> None:
    """Score < 0.7 with retries exhausted → hitl_gate (escalation)."""
    state = RunContext(critic_score=0.4, requires_approval=False, retry_count=2)
    assert orchestrator._route_critic(state) == "hitl_gate"
