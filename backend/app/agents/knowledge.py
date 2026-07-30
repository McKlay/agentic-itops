from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.agents.base import BaseAgent, _now, _output_id
from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import AgentOutput, RunContext
from app.tools.registry import ToolRegistry

KNOWLEDGE_SYSTEM_PROMPT = """\
You are SwiftAssist, the IT Operations knowledge assistant for P&G.
You help IT operations staff resolve incidents and follow procedures quickly and accurately.
Your answers are clear, concise, and professionally written — like guidance from a senior colleague, not a manual.

=== STEP 1 — CLASSIFY THE QUERY ===

Before retrieving anything, assess the query type:

ANSWERABLE   — a question about an IT procedure, system, error, or process that KB articles
               would cover. Proceed to retrieval.

AMBIGUOUS    — the question is too vague to retrieve useful content (e.g. "it's not working",
               "what should I do?"). Do NOT retrieve. Set gap_detected=false, confidence=0.50,
               and write an answer asking the user to clarify — specify what system, error
               message, or process they are asking about.

OUT_OF_SCOPE — the question is unrelated to IT operations (e.g. personal questions, general
               knowledge, HR, finance). Do NOT retrieve. Set gap_detected=false, confidence=0.0,
               and politely decline and redirect to IT support channels.

SENSITIVE    — the query asks for credentials, access bypasses, or security-sensitive config.
               Do NOT retrieve. Decline and advise the user to follow the proper access
               management process.

=== STEP 2 — QUERY NORMALIZATION & RETRIEVAL (ANSWERABLE queries only) ===

Before calling hybrid_search, normalize the search query:

a) Read the current user message and all prior conversation turns.
b) Identify which prior turns are TOPICALLY RELATED to the current message
   (same system, same process, same incident, or a direct follow-up question).
c) From the current message plus only the relevant prior turns, synthesize a single,
   focused search query that:
   - Preserves key technical terms: system names, transaction codes (e.g. FB03, AL11),
     process names, error conditions, and document types from the current message.
   - Adds relevant disambiguation context from prior turns ONLY if it narrows the
     same topic (e.g. a prior turn that clarified the company code or system in scope).
   - EXCLUDES topics from prior turns that are about a different system, process, or
     incident — do not let unrelated prior conversation contaminate the query.
d) Use that normalized query string as the `query` argument to hybrid_search.

Retrieval steps:
1. Call hybrid_search with the normalized query.
2. Each result has: chunk (text), title (PDF filename e.g. KB0573210.pdf), chunk_id, score.
3. If fewer than 2 high-scoring chunks are returned, call get_article on the best chunk_id.
4. If retrieved content does not address the question, set gap_detected=true.

=== STEP 3 — OUTPUT ===

Return ONLY this JSON (no markdown fences, start with {, end with }):

{
  "answer": "<your full answer — see writing guide below>",
  "citations": ["KB0573210.pdf — Exact Article Title"],
  "gap_detected": false,
  "confidence": 0.95
}

=== WRITING GUIDE ===

Tone: professional and direct — like a knowledgeable colleague briefing a peer.
Avoid: "This procedure allows you to...", "Please note that...", "It is important to...",
       "In order to...", robotic preambles, and passive voice.

For PROCEDURAL questions (how-to, extract, configure, troubleshoot):

  Open with a single sentence that states what this accomplishes and where it applies.
  Then list the steps on separate numbered lines:

  1. Go to transaction SM37 and execute the relevant CBVR job.
  2. Select the finished job row and click the Spool button.
  3. ...

  If there are prerequisites or watchouts, add them after the steps as a short paragraph
  beginning with "Keep in mind:" — not "Note:" or "Please note:".

For FACTUAL questions (what is, when does, who owns):

  Answer in 2-3 sentences. No numbered list needed.

For AMBIGUOUS queries:

  Acknowledge what was asked, then ask one specific clarifying question.
  Example: "To help with that, could you share the transaction or system you're working in,
  and the exact error message you're seeing?"

For KNOWLEDGE GAP (gap_detected=true):

  Acknowledge the gap honestly and suggest next steps — raise it with the team lead,
  check with BSS, or open an incident for further investigation.

For OUT_OF_SCOPE / SENSITIVE:

  Be brief, polite, and redirect appropriately.

=== METADATA FIELDS ===
citations: one entry per source document: "KBxxxxxxx.pdf — Article Title"
           Omit if no articles were retrieved.
gap_detected: true only when relevant KB content does not exist.
confidence: 0.90-1.00 (strong KB match), 0.70-0.89 (partial match),
            0.50 (ambiguous query), 0.0 (out of scope / sensitive).

=== CRITICAL OUTPUT RULE ===
Your ENTIRE response after tool calls must be a single valid JSON object — nothing else.
Do NOT include any text, explanation, or markdown outside the JSON.
Do NOT append citations, gap_detected, or confidence as plain text after the answer string.
All metadata belongs ONLY as top-level JSON keys, not inside the "answer" value.
Start your response with { and end with }.
Example of CORRECT output:
{"answer": "Step 1. Open SM37...", "citations": ["KB0573210.pdf — Title"], "gap_detected": false, "confidence": 0.95}
"""

_GAP_ANSWER = (
    "There are no existing KB articles that cover this specific scenario. "
    "Recommended next steps: raise this with your team lead or BSS, or open an incident "
    "for further investigation so a new KB article can be created."
)


class KnowledgeAgent(BaseAgent):
    """RAG retrieval agent — hybrid_search + get_article + gap detection.

    Tools: hybrid_search, get_article
    Output: synthesised answer with citations; gap_detected flag when < 2 articles match.
    Requires approval: False (read-only — no ITSM writes).
    """

    TOOL_NAMES = ["hybrid_search", "get_article"]

    def __init__(
        self,
        llm: AzureOpenAIConnector,
        tool_registry: ToolRegistry,
    ) -> None:
        super().__init__(
            agent_id="knowledge_agent",
            llm=llm,
            tool_registry=tool_registry,
            tool_names=self.TOOL_NAMES,
        )

    def _build_messages(self, state: RunContext) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT}
        ]
        # Append sliding window of conversation (last 20 messages)
        for msg in state.messages[-20:]:
            if hasattr(msg, "type"):
                role = "user" if msg.type == "human" else "assistant"
                messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                messages.append(msg)
        # Inject prior evidence if a retry is in progress
        if state.evidence:
            evidence_block = "\n".join(state.evidence)
            messages.append(
                {"role": "system", "content": f"Previously retrieved evidence:\n{evidence_block}"}
            )
        return messages

    def _parse_output(self, response: Any, state: RunContext) -> AgentOutput:
        import json as _json

        content = response.choices[0].message.content or ""
        content = content.strip()
        # Strip markdown fences: ```json ... ``` or ``` ... ```
        if content.startswith("```"):
            lines = content.splitlines()
            # Drop the opening fence line (```json or ```) and closing fence
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            content = "\n".join(inner).strip()

        gap_detected = False
        try:
            data = _json.loads(content)
        except (_json.JSONDecodeError, TypeError):
            # Fallback: find the first {...} block in the response
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    data = _json.loads(match.group())
                    self.logger.warning(
                        "[knowledge_agent] JSON extracted via regex fallback — "
                        "LLM did not return bare JSON"
                    )
                except (_json.JSONDecodeError, TypeError):
                    data = None
            else:
                data = None

        if data is not None:
            answer = data.get("answer", "").strip() or content
            citations: list[str] = data.get("citations", [])
            confidence = float(data.get("confidence", 0.8))
            gap_detected = bool(data.get("gap_detected", False))
        else:
            answer = content
            citations = []
            confidence = 0.6
            self.logger.warning(
                "[knowledge_agent] Could not parse LLM output as JSON — "
                "returning raw content with degraded confidence"
            )

        if gap_detected:
            answer = _GAP_ANSWER
            confidence = 0.5

        self.logger.info(
            "[knowledge_agent] Parsed output — confidence=%.2f citations=%d gap=%s answer=%r",
            confidence,
            len(citations),
            gap_detected,
            answer[:120],
        )

        return AgentOutput(
            output_id=_output_id(),
            agent_id=self.agent_id,
            intent=state.intent,
            summary=answer,
            detail="",
            steps=[],
            notes=[],
            citations=citations,
            citation_urls={},
            requires_approval=False,
            confidence=confidence,
            created_at=_now(),
        )
