from __future__ import annotations

import json
import logging
from typing import Any

from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import RunContext

logger = logging.getLogger("agents.supervisor")

# ---------------------------------------------------------------------------
# Intent routing table
# ---------------------------------------------------------------------------
INTENT_ROUTING: dict[str, dict[str, Any]] = {
    "triage_incident":      {"agents": ["incident_agent"],   "requires_approval": True},
    "search_knowledge":     {"agents": ["knowledge_agent"],  "requires_approval": False},
    "analyze_problem":      {"agents": ["problem_agent"],    "requires_approval": True},
    "generate_postmortem":  {"agents": ["postmortem_agent"], "requires_approval": True},
    "review_governance":    {"agents": ["governance_agent"], "requires_approval": True},
    "general_chat":         {"agents": [],                   "requires_approval": False},
}

SUPERVISOR_PROMPT = """\
You are the Supervisor Agent for an AI-powered IT Operations platform at P&G.
Your sole responsibility is to classify the user's intent and route it to the
correct specialist agent.

Respond with a JSON object ONLY — no prose, no markdown fences.
Schema:
{
  "intent": "<intent_value>",
  "agents": ["<agent_name>", ...],
  "requires_approval": <true|false>,
  "rationale": "<one sentence>"
}

Allowed intent values and their routing:
- "triage_incident"     → incident_agent     (requires_approval: true)
- "search_knowledge"    → knowledge_agent    (requires_approval: false)
- "analyze_problem"     → problem_agent      (requires_approval: true)
- "generate_postmortem" → postmortem_agent   (requires_approval: true)
- "review_governance"   → governance_agent   (requires_approval: true)
- "general_chat"        → (no agent)         (requires_approval: false)

Guidelines:
- Prefer "search_knowledge" for questions about procedures, runbooks, how-to, status
  lookups (e.g. "why is X on hold?", "what does Y status mean?"), or requests for
  information about a process or business object.
- Prefer "triage_incident" ONLY when the user explicitly reports an active outage,
  system degradation, or asks to create/update an incident ticket.
- Prefer "analyze_problem" when the user asks to investigate recurring incidents,
  identify root cause trends, or perform a formal problem record analysis (e.g.
  "why does this keep happening?", "open a problem for INC123456").
- Prefer "generate_postmortem" when the user asks to write, draft, or generate a
  post-incident review, RCA document, or postmortem report (e.g. "create an RCA for
  last night's outage", "write the postmortem for INC123456").
- Prefer "review_governance" when the user asks about change management, CAB approvals,
  compliance checks, or policy review (e.g. "review this change request", "does this
  meet our change policy?", "check CAB approval status").
- Prefer "general_chat" for greetings, thanks, or out-of-scope queries.
- Never invent intent values outside the list above.
- If the critic_feedback field is non-empty in the conversation, incorporate it.
"""


def _parse_classification(text: str) -> dict[str, Any]:
    """Extract the JSON classification dict from the LLM response text."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        intent = data.get("intent", "general_chat")
        if intent not in INTENT_ROUTING:
            intent = "general_chat"
        routing = INTENT_ROUTING[intent]
        return {
            "intent": intent,
            "selected_agents": data.get("agents", routing["agents"]),
            "requires_approval": data.get("requires_approval", routing["requires_approval"]),
        }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Supervisor could not parse LLM JSON; defaulting to general_chat")
        return {"intent": "general_chat", "selected_agents": [], "requires_approval": False}


class SupervisorAgent:
    """Intent classification agent — routes requests to specialist executor agents.

    Does not extend ``BaseAgent`` because it never calls tools.
    Returns a plain dict update for LangGraph state: intent, selected_agents,
    requires_approval.
    """

    def __init__(self, llm: AzureOpenAIConnector) -> None:
        self.llm = llm

    async def run(self, state: RunContext) -> dict[str, Any]:
        """Classify intent and return routing decision."""
        # Build message list: system prompt + conversation history
        # Inject critic feedback if a retry is in progress
        system_content = SUPERVISOR_PROMPT
        if state.critic_feedback:
            system_content += (
                f"\n\nPrevious attempt critic feedback (retry #{state.retry_count}):\n"
                f"{state.critic_feedback}\n"
                "Adjust the routing or agent selection accordingly."
            )

        messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
        for msg in state.messages[-20:]:  # sliding window
            if hasattr(msg, "type"):  # LangChain message
                role = "user" if msg.type == "human" else "assistant"
                messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                messages.append(msg)

        response = await self.llm.chat_completion(messages=messages, temperature=0.2)
        content = response.choices[0].message.content or ""
        classification = _parse_classification(content)

        logger.info(
            "Supervisor classified intent=%r agents=%s approval=%s",
            classification["intent"],
            classification["selected_agents"],
            classification["requires_approval"],
        )
        return classification
