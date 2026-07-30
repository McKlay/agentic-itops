from __future__ import annotations

import json
import logging
from typing import Any

from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import AgentOutput, RunContext

logger = logging.getLogger("agents.critic")

CRITIC_PROMPT = """\
You are the Critic Agent for P&G IT Operations AI platform.
Evaluate the quality of the agent output(s) provided and return a JSON score.

Scoring criteria (each 0–1, averaged):
- Accuracy:    Is the answer factually correct and grounded in the evidence?
- Completeness: Does it fully address the user's question?
- Clarity:     Is it clearly written and well-structured?
- Safety:      Does it avoid hallucination, harmful advice, or unsupported claims?

Respond with JSON ONLY (no markdown fences):
{
  "score": <0.0-1.0>,
  "accuracy": <0.0-1.0>,
  "completeness": <0.0-1.0>,
  "clarity": <0.0-1.0>,
  "safety": <0.0-1.0>,
  "feedback": "<one or two sentences of actionable improvement suggestions>"
}

Score ≥ 0.7 is passing. Score < 0.7 triggers a retry with your feedback.
"""


def _format_outputs(outputs: list[AgentOutput]) -> str:
    lines = []
    for o in outputs:
        lines.append(f"Agent: {o.agent_id}")
        lines.append(f"Summary: {o.summary}")
        if o.detail:
            lines.append(f"Detail: {o.detail[:800]}")
        if o.citations:
            lines.append(f"Citations: {', '.join(o.citations)}")
        lines.append(f"Confidence: {o.confidence}")
        lines.append("---")
    return "\n".join(lines)


def _parse_score(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        return {
            "score": float(data.get("score", 0.5)),
            "feedback": str(data.get("feedback", "")),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Critic could not parse LLM JSON; defaulting score to 0.5")
        return {"score": 0.5, "feedback": "Unable to parse critic score — defaulting to 0.5."}


class CriticAgent:
    """Quality scoring agent — evaluates AgentOutput and decides pass / retry / escalate.

    Does not extend BaseAgent — it never calls tools.
    Returns: critic_score, critic_feedback, retry_count (incremented when score < 0.7).
    """

    PASS_THRESHOLD = 0.7

    def __init__(self, llm: AzureOpenAIConnector) -> None:
        self.llm = llm

    async def run(self, state: RunContext) -> dict[str, Any]:
        """Score agent outputs and return quality gate decision."""
        if not state.agent_outputs:
            logger.warning("CriticAgent called with no agent_outputs — passing through")
            return {"critic_score": 1.0, "critic_feedback": ""}

        outputs_text = _format_outputs(state.agent_outputs)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": f"Please evaluate these agent outputs:\n\n{outputs_text}"},
        ]

        response = await self.llm.chat_completion(messages=messages, temperature=0.2)
        content = response.choices[0].message.content or ""
        result = _parse_score(content)

        score = result["score"]
        feedback = result["feedback"]
        retry_count = state.retry_count + (1 if score < self.PASS_THRESHOLD else 0)

        logger.info(
            "Critic score=%.2f threshold=%.2f retry_count=%d",
            score, self.PASS_THRESHOLD, retry_count,
        )
        return {
            "critic_score": score,
            "critic_feedback": feedback,
            "retry_count": retry_count,
        }
