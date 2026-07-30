from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent, _now, _output_id
from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import AgentOutput, RunContext
from app.tools.registry import ToolRegistry

_STUB_MSG = (
    "GovernanceAgent is not yet implemented. "
    "Activate after Application Insights is provisioned and telemetry tools are wired."
)


class GovernanceAgent(BaseAgent):
    """Alert governance review agent — STUB.

    Tools (planned): get_metrics, get_signals
    Requires approval: True (may modify alert rules).
    """

    TOOL_NAMES = ["get_metrics", "get_signals"]

    def __init__(
        self,
        llm: AzureOpenAIConnector,
        tool_registry: ToolRegistry,
    ) -> None:
        super().__init__(
            agent_id="governance_agent",
            llm=llm,
            tool_registry=tool_registry,
            tool_names=self.TOOL_NAMES,
        )

    def _build_messages(self, state: RunContext) -> list[dict[str, Any]]:
        return [{"role": "system", "content": _STUB_MSG}]

    def _parse_output(self, response: Any, state: RunContext) -> AgentOutput:
        return AgentOutput(
            output_id=_output_id(),
            agent_id=self.agent_id,
            intent=state.intent,
            summary=_STUB_MSG,
            requires_approval=True,
            confidence=0.0,
            created_at=_now(),
        )

    async def run(self, state: RunContext) -> dict[str, Any]:
        self.logger.warning("GovernanceAgent is a stub — returning placeholder output")
        output = self._parse_output(None, state)
        return {"agent_outputs": state.agent_outputs + [output], "tool_results": state.tool_results}
