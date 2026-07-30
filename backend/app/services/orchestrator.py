from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from app.agents.critic import CriticAgent
from app.agents.governance import GovernanceAgent
from app.agents.incident import IncidentAgent
from app.agents.knowledge import KnowledgeAgent
from app.agents.postmortem import PostmortemAgent
from app.agents.problem import ProblemRcaAgent
from app.agents.supervisor import SupervisorAgent
from app.config import Settings
from app.connectors import ConnectorBundle
from app.memory.checkpointer import get_checkpointer
from app.models.agent import AgentOutput, RunContext
from app.store.base import DomainStoreInterface
from app.tools.collaboration_tools import make_collaboration_tools
from app.tools.itsm_tools import make_itsm_tools
from app.tools.registry import ToolRegistry
from app.tools.schemas import ALL_SCHEMAS
from app.tools.search_tools import make_search_tools
from app.tools.telemetry_tools import get_metrics, get_signals

logger = logging.getLogger(__name__)

# Maximum retry attempts; matches CriticAgent.PASS_THRESHOLD logic
_MAX_RETRIES = 2


class Orchestrator:
    """Build, compile, and execute the LangGraph agent pipeline.

    Lifecycle::

        orchestrator = Orchestrator(settings, connectors, store)
        await orchestrator.initialize()   # called once at startup
        state = await orchestrator.run(message, thread_id, user)
    """

    def __init__(
        self,
        settings: Settings,
        connectors: ConnectorBundle,
        store: DomainStoreInterface,
    ) -> None:
        self._settings = settings
        self._connectors = connectors
        self._store = store
        self._graph: CompiledStateGraph | None = None

        # Agents — constructed during initialize()
        self._supervisor: SupervisorAgent | None = None
        self._incident: IncidentAgent | None = None
        self._knowledge: KnowledgeAgent | None = None
        self._problem: ProblemRcaAgent | None = None
        self._postmortem: PostmortemAgent | None = None
        self._governance: GovernanceAgent | None = None
        self._critic: CriticAgent | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Build tool registry, instantiate agents, compile graph."""
        registry = self._build_registry()

        llm = self._connectors.azure_openai
        self._supervisor = SupervisorAgent(llm=llm)
        self._incident = IncidentAgent(llm=llm, tool_registry=registry)
        self._knowledge = KnowledgeAgent(llm=llm, tool_registry=registry)
        self._problem = ProblemRcaAgent(llm=llm, tool_registry=registry)
        self._postmortem = PostmortemAgent(llm=llm, tool_registry=registry)
        self._governance = GovernanceAgent(llm=llm, tool_registry=registry)
        self._critic = CriticAgent(llm=llm)

        checkpointer = await get_checkpointer(self._settings)
        self._graph = self._build_graph(checkpointer)
        logger.info("Orchestrator initialized — graph compiled with %d nodes", 10)

    async def run(self, message: str, thread_id: str, user: dict) -> dict[str, Any]:
        """Invoke the graph for a new user message."""
        self._assert_ready()
        config = {"configurable": {"thread_id": thread_id}}
        input_state: dict[str, Any] = {
            "messages": [HumanMessage(content=message)],
            "thread_id": thread_id,
            "user": user,
            # Reset ephemeral per-turn state so prior checkpointed values don't
            # accumulate across conversation turns (fixes agent_outputs=N bug).
            "agent_outputs": [],
            "tool_results": [],
            "evidence": [],
            "retry_count": 0,
            "critic_score": None,
            "critic_feedback": "",
            "approval_decision": None,
            "general_chat_reply": "",
            "final_response": "",
        }
        return await self._graph.ainvoke(input_state, config=config)  # type: ignore[union-attr]

    async def resume(self, thread_id: str, decision: dict) -> dict[str, Any]:
        """Resume a paused graph after a HITL approval decision."""
        self._assert_ready()
        config = {"configurable": {"thread_id": thread_id}}
        return await self._graph.ainvoke(  # type: ignore[union-attr]
            Command(resume=decision), config=config
        )

    async def get_thread_state(self, thread_id: str) -> dict:
        """Return the latest LangGraph checkpoint state for a thread."""
        self._assert_ready()
        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)  # type: ignore[union-attr]
        return state.values if state else {}

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        c = self._connectors

        hybrid_search, get_article = make_search_tools(c.azure_search, c.azure_openai, self._settings)
        lookup_incident, create_incident, update_incident = make_itsm_tools(c.servicenow)
        send_teams_notification = make_collaboration_tools(c.teams)

        for name, handler in [
            ("hybrid_search", hybrid_search),
            ("get_article", get_article),
            ("lookup_incident", lookup_incident),
            ("create_incident", create_incident),
            ("update_incident", update_incident),
            ("get_signals", get_signals),
            ("get_metrics", get_metrics),
            ("send_teams_notification", send_teams_notification),
        ]:
            registry.register(name, handler, ALL_SCHEMAS[name])

        return registry

    def _build_graph(self, checkpointer: Any) -> CompiledStateGraph:
        graph: StateGraph = StateGraph(RunContext)

        # Nodes
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("incident_agent", self._incident_node)
        graph.add_node("knowledge_agent", self._knowledge_node)
        graph.add_node("problem_agent", self._problem_node)
        graph.add_node("postmortem_agent", self._postmortem_node)
        graph.add_node("governance_agent", self._governance_node)
        graph.add_node("general_chat_agent", self._general_chat_node)
        graph.add_node("critic", self._critic_node)
        graph.add_node("hitl_gate", self._hitl_node)
        graph.add_node("response_formatter", self._format_node)

        # Entry + routing
        graph.set_entry_point("supervisor")
        graph.add_conditional_edges("supervisor", self._route_to_agent)

        # Agent → critic
        for agent_node in [
            "incident_agent", "knowledge_agent", "problem_agent",
            "postmortem_agent", "governance_agent",
        ]:
            graph.add_edge(agent_node, "critic")

        # general_chat bypasses critic — goes straight to formatter
        graph.add_edge("general_chat_agent", "response_formatter")

        # Critic → conditional
        graph.add_conditional_edges("critic", self._route_critic)

        # Terminal edges
        graph.add_edge("hitl_gate", "response_formatter")
        graph.add_edge("response_formatter", END)

        return graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["hitl_gate"],
        )

    # ------------------------------------------------------------------
    # Node functions
    # ------------------------------------------------------------------

    async def _supervisor_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=supervisor thread=%s", state.thread_id)
        return await self._supervisor.run(state)  # type: ignore[union-attr]

    async def _incident_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=incident_agent thread=%s", state.thread_id)
        return await self._incident.run(state)  # type: ignore[union-attr]

    async def _knowledge_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=knowledge_agent thread=%s", state.thread_id)
        return await self._knowledge.run(state)  # type: ignore[union-attr]

    async def _problem_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=problem_agent thread=%s", state.thread_id)
        return await self._problem.run(state)  # type: ignore[union-attr]

    async def _postmortem_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=postmortem_agent thread=%s", state.thread_id)
        return await self._postmortem.run(state)  # type: ignore[union-attr]

    async def _governance_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=governance_agent thread=%s", state.thread_id)
        return await self._governance.run(state)  # type: ignore[union-attr]

    async def _general_chat_node(self, state: RunContext) -> dict:
        """Handle conversational turns that don't require a specialist agent."""
        logger.info("[graph] Node=general_chat_agent thread=%s", state.thread_id)
        llm = self._connectors.azure_openai
        system = (
            "You are SwiftAssist AI, a friendly IT Operations assistant at P&G. "
            "Respond naturally and concisely to the user's message. "
            "Do not fabricate technical details. Keep the reply to 1-3 sentences."
        )
        messages: list[dict] = [{"role": "system", "content": system}]
        for msg in state.messages[-10:]:
            if hasattr(msg, "type"):
                role = "user" if msg.type == "human" else "assistant"
                messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                messages.append(msg)
        response = await llm.chat_completion(messages=messages, temperature=0.7)
        reply = response.choices[0].message.content or ""
        logger.info("[graph] general_chat_agent reply=%r thread=%s", reply[:80], state.thread_id)
        return {"general_chat_reply": reply}

    async def _critic_node(self, state: RunContext) -> dict:
        logger.info("[graph] Node=critic thread=%s", state.thread_id)
        return await self._critic.run(state)  # type: ignore[union-attr]

    async def _hitl_node(self, state: RunContext) -> dict:
        """Pause graph execution pending human approval via LangGraph interrupt."""
        pending: list[AgentOutput] = [
            o for o in state.agent_outputs if o.requires_approval
        ]
        if pending:
            decision = interrupt(
                {
                    "type": "approval_required",
                    "outputs": [o.model_dump() for o in pending],
                }
            )
            for output in pending:
                output.status = decision.get("decision", "pending")
            return {"approval_decision": decision}
        return {}

    async def _format_node(self, state: RunContext) -> dict:
        """Assemble the final reply text from the last agent output."""
        logger.info("[graph] Node=response_formatter thread=%s", state.thread_id)
        outputs: list[AgentOutput] = state.agent_outputs or []
        if outputs:
            last = outputs[-1]
            reply = last.summary  # already the full answer (summary + steps + notes in prose)
            logger.info(
                "[graph] Final response — agent=%s confidence=%.2f citations=%d reply=%r",
                last.agent_id,
                last.confidence,
                len(last.citations or []),
                reply[:120],
            )
        else:
            reply = state.general_chat_reply or "I'm sorry, I wasn't able to generate a response. Please try again."
            if state.general_chat_reply:
                logger.info("[graph] General chat reply thread=%s reply=%r", state.thread_id, reply[:80])
            else:
                logger.warning("[graph] No agent outputs — returning fallback reply thread=%s", state.thread_id)

        return {"final_response": reply}

    # ------------------------------------------------------------------
    # Conditional edge functions
    # ------------------------------------------------------------------

    def _route_to_agent(self, state: RunContext) -> str:
        """Route from supervisor to the correct executor node."""
        agents = getattr(state, "selected_agents", None) or []
        if not agents:
            # general_chat has no selected agents — send to its dedicated node
            return "general_chat_agent" if state.intent == "general_chat" else "response_formatter"

        first = agents[0]
        node_map = {
            "incident_agent": "incident_agent",
            "knowledge_agent": "knowledge_agent",
            "problem_agent": "problem_agent",
            "postmortem_agent": "postmortem_agent",
            "governance_agent": "governance_agent",
        }
        return node_map.get(first, "response_formatter")

    def _route_critic(self, state: RunContext) -> str:
        """Route from critic based on quality score and approval requirements."""
        score: float = getattr(state, "critic_score", 0.0) or 0.0
        requires_approval: bool = getattr(state, "requires_approval", False) or False
        retry_count: int = getattr(state, "retry_count", 0) or 0

        if score >= 0.7:
            if requires_approval:
                return "hitl_gate"
            return "response_formatter"

        # Score below threshold
        if retry_count < _MAX_RETRIES:
            return "supervisor"

        # Max retries exhausted — escalate
        return "hitl_gate"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _assert_ready(self) -> None:
        if self._graph is None:
            raise RuntimeError(
                "Orchestrator.initialize() must be awaited before use."
            )
