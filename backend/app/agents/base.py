from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import AgentOutput, RunContext, ToolCallResult
from app.tools.registry import ToolRegistry


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _output_id() -> str:
    return f"out_{uuid.uuid4().hex[:12]}"


class BaseAgent(ABC):
    """Abstract agent implementing the ReAct (Reason + Act) loop.

    Aligned with the PyGentic ``RolePlayingAgent`` pattern:
    - Each agent is a single LangGraph node function (``run()``)
    - Tools are invoked via OpenAI function-call schemas
    - Results accumulate in ``RunContext`` (Tier 2 working memory)
    - ``run()`` returns a dict update consumed by LangGraph state

    Migration path to full PyGentic: wrap ``run()`` in
    ``RolePlayingAgent.build_workflow()`` — the interface is compatible.
    """

    MAX_STEPS = 5

    def __init__(
        self,
        agent_id: str,
        llm: AzureOpenAIConnector,
        tool_registry: ToolRegistry,
        tool_names: list[str],
    ) -> None:
        self.agent_id = agent_id
        self.llm = llm
        self.tool_registry = tool_registry
        self.tool_schemas = tool_registry.get_schemas(tool_names)
        self.logger = logging.getLogger(f"agents.{agent_id}")

    async def run(self, state: RunContext) -> dict[str, Any]:
        """Execute the ReAct loop: reason → tool_call → observe → repeat.

        Returns a partial state dict for LangGraph (never the full RunContext).
        """
        messages = self._build_messages(state)
        accumulated_tool_results: list[ToolCallResult] = []

        self.logger.info(
            "[%s] Starting ReAct loop — intent=%s max_steps=%d",
            self.agent_id, state.intent, self.MAX_STEPS,
        )

        for step in range(self.MAX_STEPS):
            self.logger.info("[%s] ReAct step %d/%d", self.agent_id, step + 1, self.MAX_STEPS)

            response = await self.llm.chat_completion(
                messages=messages,
                tools=self.tool_schemas or None,
                temperature=0.2,
            )
            choice = response.choices[0]

            # --- Act: execute tool calls ---
            raw_tool_calls = getattr(choice.message, "tool_calls", None) or []
            if raw_tool_calls:
                # Append assistant message with tool_calls intact
                messages.append(
                    {
                        "role": "assistant",
                        "content": choice.message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in raw_tool_calls
                        ],
                    }
                )
                for tc in raw_tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                        self.logger.info(
                            "[%s] Tool call → %s args=%s",
                            self.agent_id, tc.function.name,
                            json.dumps(args, default=str)[:200],
                        )
                        result = await self.tool_registry.execute(tc.function.name, args)
                        error: str | None = None
                        result_preview = json.dumps(result, default=str)[:300]
                        self.logger.info(
                            "[%s] Tool result ← %s result=%s",
                            self.agent_id, tc.function.name, result_preview,
                        )
                    except Exception as exc:  # noqa: BLE001
                        result = {"error": str(exc)}
                        error = str(exc)
                        self.logger.error(
                            "[%s] Tool error — %s: %s",
                            self.agent_id, tc.function.name, exc,
                        )

                    tool_result = ToolCallResult(
                        tool_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                        result=result,
                        error=error,
                    )
                    accumulated_tool_results.append(tool_result)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
            else:
                # --- Observe: agent finished reasoning ---
                self.logger.info(
                    "[%s] Reasoning complete after %d step(s) — parsing output",
                    self.agent_id, step + 1,
                )
                # Merge accumulated tool results into state so _parse_output
                # can access all tool call results from this run.
                parse_state = state.model_copy(
                    update={"tool_results": state.tool_results + accumulated_tool_results}
                )
                output = self._parse_output(response, parse_state)
                return {
                    "agent_outputs": state.agent_outputs + [output],
                    "tool_results": state.tool_results + accumulated_tool_results,
                    "messages": [
                        AIMessage(content=choice.message.content or "")
                    ],
                }

        # Max steps exceeded — return low-confidence fallback
        self.logger.warning(
            "Agent '%s' reached MAX_STEPS=%d without finishing", self.agent_id, self.MAX_STEPS
        )
        return self._fallback_output(state)

    @abstractmethod
    def _build_messages(self, state: RunContext) -> list[dict[str, Any]]:
        """Build the message array sent to the LLM (system prompt + context)."""

    @abstractmethod
    def _parse_output(self, response: Any, state: RunContext) -> AgentOutput:
        """Parse the final LLM response into a structured ``AgentOutput``."""

    def _fallback_output(self, state: RunContext) -> dict[str, Any]:
        """Return a low-confidence output when MAX_STEPS is exceeded."""
        output = AgentOutput(
            output_id=_output_id(),
            agent_id=self.agent_id,
            intent=state.intent,
            summary=f"{self.agent_id} could not reach a conclusion within {self.MAX_STEPS} steps.",
            detail="",
            requires_approval=True,
            confidence=0.0,
            created_at=_now(),
        )
        return {
            "agent_outputs": state.agent_outputs + [output],
            "tool_results": state.tool_results,
        }
