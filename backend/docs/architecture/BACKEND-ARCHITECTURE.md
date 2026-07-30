# Technical Solution Document (TSD) — Part 1

## SwiftAssist AI · Backend Architecture
## Overview & Architecture

**Version:** 2.0  
**Date:** April 28, 2026  
**Author:** AI Operations Concierge Team  
**Classification:** Internal Use — Enterprise IT Operations

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-24 | CM Sarte | Initial backend architecture scaffold |
| 1.1 | 2026-04-26 | CM Sarte | Added orchestration and agent pipeline |
| 2.0 | 2026-04-28 | CM Sarte | Three-tier memory architecture, LangGraph checkpointing, framework alignment, Terraform IaC |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Solution Overview](#2-solution-overview)
3. [Architecture](#3-architecture)
4. [Memory Architecture](#4-memory-architecture)
5. [Orchestration Deep Dive](#5-orchestration-deep-dive)
6. [Agent Architecture](#6-agent-architecture)
7. [Data Architecture](#7-data-architecture)
8. [Infrastructure](#8-infrastructure)
9. [Framework Migration Path](#9-framework-migration-path)
10. [Appendices](#10-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This document provides the authoritative backend architecture specification for the SwiftAssist AI Operations Concierge — an approval-first, enterprise agentic IT Operations platform built for enterprise operations teams. It defines the system's layered architecture, three-tier memory design, LangGraph orchestration, agent pipeline, connector abstractions, and Azure infrastructure.

### 1.2 Business Context

- **Client:** Enterprise client
- **Delivery Team:** Engineering team
- **Objective:** AI-powered IT operations chatbot for incident triage, knowledge retrieval, RCA generation, and ServiceNow automation
- **Core Principle:** All agent-generated actions require explicit human approval before modifying production systems
- **Framework Alignment:** Target enterprise agentic workflow framework

### 1.3 Technical Scope

| Capability | Description |
|------------|-------------|
| **Incident Triage** | AI-powered severity classification, resolution drafting, ServiceNow integration |
| **Knowledge Retrieval** | RAG via Azure AI Search — hybrid BM25 + vector search over KB articles |
| **Root Cause Analysis** | Multi-agent RCA pipeline with evidence gathering and corrective action plans |
| **Blameless Postmortems** | Structured postmortem generation with review agendas |
| **Alert Governance** | Monitoring rule drafts and alert tuning recommendations |
| **Approval Workflow** | Human-in-the-loop (HITL) approval via LangGraph `interrupt()` |

### 1.4 Technology Stack Summary

| Layer | Core Technologies | Azure Services |
|-------|-------------------|----------------|
| **Web Framework** | FastAPI ≥ 0.115, Pydantic v2, uvicorn | Azure App Service (Linux, Python 3.11) |
| **Orchestration** | LangGraph ≥ 0.2, LangChain Core ≥ 0.3 | — |
| **AI / LLM** | OpenAI SDK (Azure OpenAI), gpt-5.3-chat | Azure OpenAI Service |
| **Embeddings** | text-embedding-3-large (3072 dimensions) | Azure OpenAI Service |
| **Knowledge** | azure-search-documents SDK | Azure AI Search |
| **ITSM** | httpx → ServiceNow REST API | — |
| **Conversation Memory** | LangGraph MemorySaver (POC) → AsyncRedisSaver (prod) | Azure Cache for Redis |
| **Domain Store** | InMemoryStore (POC) → CosmosStore (prod) | Azure Cosmos DB (MongoDB API) |
| **Auth** | python-jose (JWT), Entra ID | Microsoft Entra ID |
| **Notifications** | httpx → Adaptive Card webhook | Microsoft Teams |
| **IaC** | Terraform (9 modules) | Azure Resource Manager |

---

## 2. Solution Overview

### 2.1 Approval-First Agentic Platform

The backend implements an **approval-first** pattern: every agent output that modifies external systems sets `requires_approval=True` and must pass through a HITL gate before execution. No agent autonomously writes to ServiceNow, Teams, or any production system.

**Workflow:**
1. User sends a natural language message via chat interface
2. Supervisor agent classifies intent and routes to executor agents
3. Executor agents reason, gather evidence, and draft outputs using tools
4. Critic agent scores output quality (retry if below threshold)
5. HITL gate pauses execution for human approval (via LangGraph `interrupt()`)
6. On approval, dispatcher pushes approved outputs to external systems
7. Full audit trail persisted to Domain Store

### 2.2 Three-Tier Memory Design

The backend separates state into three independent memory tiers — each with distinct lifecycle, persistence, and access patterns:

| Tier | Purpose | Lifecycle | POC Implementation | Production Implementation |
|------|---------|-----------|---------------------|---------------------------|
| **Tier 1** | Conversation Memory | Multi-turn (per thread) | `MemorySaver` (in-process) | `AsyncRedisSaver` (Azure Cache for Redis) |
| **Tier 2** | Working Memory | Single request (per graph run) | `RunContext` (Pydantic model) | `RunContext` (same) |
| **Tier 3** | Domain Store | Persistent (application lifetime) | `InMemoryStore` (seeded demo data) | `CosmosStore` (Azure Cosmos DB MongoDB API) |

### 2.3 Framework Alignment

This architecture is designed for future migration to a target enterprise agentic framework. Key alignment points:

- **Checkpointer cascade** mirrors the target framework's priority resolution pattern (custom → Redis → MemorySaver)
- **Agent composition** follows a role-playing agent plus supervisor agent pattern
- **Tool schemas** use OpenAI function-call format (same as LangChain `@tool`)
- **Domain store** uses MongoDB API aligned with Cosmos-style store abstractions
- **Graph registration** targets a registry-driven `flows.json` style configuration

---

## 3. Architecture

### 3.1 Architectural Principles

1. **Approval-First:** Every `AgentOutput` with side effects flows through an `ApprovalTask` before dispatch
2. **Connector Abstraction:** External systems accessed only through typed connector classes with `_live` fallback
3. **Read from Search, Write to ITSM:** Azure AI Search is the knowledge read layer; ServiceNow is the write target
4. **In-Memory Fallback:** Every connector degrades gracefully when its external service is unconfigured
5. **Auditability:** Every state-changing operation logged via `store.log_event(kind, payload)`
6. **No Direct Secrets:** All credentials from environment variables only

### 3.2 Five-Layer Backend Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: FASTAPI APPLICATION                                       │
│  ├── Auth middleware (Entra ID JWT validation)                      │
│  ├── Request logging middleware (structured JSON)                   │
│  ├── Routes: /api/chat, /api/dashboard, /v1/threads, /healthz       │
│  └── Global error handlers (HTTPException, KeyError)                │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2: ORCHESTRATION (LangGraph StateGraph)                      │
│  ├── Supervisor node — LLM intent classification → agent routing    │
│  ├── Executor agent nodes — ReAct tool-calling reasoning loops      │
│  ├── Critic node — quality scoring, retry logic, escalation         │
│  └── HITL gate — approval via LangGraph interrupt() / resume()      │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3: TOOLS (OpenAI function-call schemas)                      │
│  ├── itsm_tools → ServiceNowConnector                               │
│  ├── search_tools → AzureSearchConnector                            │
│  ├── telemetry_tools → TelemetryConnector                           │
│  └── collaboration_tools → TeamsConnector                           │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 4: CONNECTORS (typed clients with _live fallback)            │
│  ├── ServiceNowConnector (httpx → SNOW REST API)                    │
│  ├── AzureOpenAIConnector (openai SDK → gpt-5.3-chat)               │
│  ├── AzureSearchConnector (azure-search-documents SDK)              │
│  ├── TeamsConnector (httpx → Adaptive Card webhook)                 │
│  └── TelemetryConnector (in-memory → Application Insights)          │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 5: MEMORY & STATE (three-tier)                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Tier 1: CONVERSATION MEMORY (LangGraph checkpointing)       │    │
│  │   POC:  MemorySaver (in-process, zero dependencies)         │    │
│  │   PROD: AsyncRedisSaver → Azure Cache for Redis (SSL)       │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │ Tier 2: WORKING MEMORY (transient per-request)              │    │
│  │   RunContext (Pydantic) — graph state schema, disposed EOL  │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │ Tier 3: DOMAIN STORE (persistent application state)         │    │
│  │   POC:  InMemoryStore (seeded demo data)                    │    │
│  │   PROD: CosmosStore → Azure Cosmos DB (MongoDB API)         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  KNOWLEDGE LAYER (read-only, external)                              │
│  └── Azure AI Search index (hybrid BM25 + vector via RAG)           │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Service Communication

```
Frontend (React SPA)
    ↓ HTTPS (Authorization: Bearer {jwt})
Azure App Service (uvicorn on :8000)
    ↓ FastAPI route → Depends(get_current_user)
Orchestrator (LangGraph graph.ainvoke)
    ├── Supervisor → AzureOpenAI (chat completion)
    ├── Executors → Tools → Connectors → External APIs
    ├── Critic → AzureOpenAI (quality scoring)
    └── HITL → interrupt() → checkpoint → resume()
```

---

## 4. Memory Architecture

Each tier serves a distinct purpose with independent implementation, lifecycle, and persistence guarantees. This separation aligns with reusable agent-framework memory patterns and industry-standard AI agent designs.

### 4.1 Tier 1 — Conversation Memory (LangGraph Checkpointing)

**Purpose:** Persist graph state (messages, tool call history, node progression) across HTTP requests within a conversation thread. Enables multi-turn reasoning, HITL `interrupt()` flows, and state recovery on restart.

**Contents:**
- LangGraph checkpoint snapshots (serialized graph state per step)
- Message history (OpenAI-format messages accumulated by the graph)
- Pending interrupts (HITL approval gates waiting for human input)
- Thread metadata (thread_id, checkpoint_id, parent checkpoint)

**Mechanism:**
LangGraph's `StateGraph.compile(checkpointer=...)` accepts a `BaseCheckpointSaver`. Every graph node execution writes a checkpoint. When a new request arrives for the same `thread_id`, the graph resumes from the latest checkpoint — this is how multi-turn conversations work.

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver  # production

# POC: in-process, lost on restart
checkpointer = MemorySaver()

# Production: Azure Cache for Redis
checkpointer = AsyncRedisSaver.from_conn_info(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    ssl=True,
)
await checkpointer.setup()

# Compile graph with checkpointer
graph = workflow.compile(checkpointer=checkpointer)
```

**Checkpointer Priority Cascade** (aligned with the target framework's flow-controller pattern):

| Priority | Condition | Checkpointer |
|---|---|---|
| 1 | Graph compiled with explicit `checkpointer=` | User-provided (custom) |
| 2 | `REDIS_URL` env var is set | `AsyncRedisSaver` (Azure Cache for Redis) |
| 3 | Fallback | Module-level `MemorySaver()` singleton |

```python
# app/memory/checkpointer.py

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

# Module-level singleton — shared across all graphs in-process
_GLOBAL_CHECKPOINTER: BaseCheckpointSaver = MemorySaver()


async def get_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    """Resolve checkpointer using priority cascade."""
    if settings.redis_url:
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            saver = AsyncRedisSaver.from_conn_string(settings.redis_url)
            await saver.setup()
            logger.info("Using Redis checkpointer (Azure Cache for Redis)")
            return saver
        except Exception as e:
            logger.warning(f"Redis checkpointer failed: {e}. Falling back to MemorySaver.")
    logger.info("Using in-memory MemorySaver checkpointer")
    return _GLOBAL_CHECKPOINTER
```

**HITL via Checkpointing:**
The approval gate uses LangGraph's `interrupt()` to pause graph execution and write state to the checkpoint store. When the human approves or rejects, the graph resumes from that checkpoint with the decision injected via `Command(resume=...)`.

```python
# In the HITL gate node:
from langgraph.types import interrupt, Command

async def hitl_gate(state: RunContext) -> RunContext:
    pending = [o for o in state.agent_outputs if o.requires_approval]
    if pending:
        # Pauses execution — checkpoint saved, HTTP response returned
        decision = interrupt({
            "type": "approval_required",
            "outputs": [o.model_dump() for o in pending],
        })
        # Execution resumes here when human calls POST /v1/threads/{id}/runs
        # with Command(resume={"decision": "approved", ...})
        for output in pending:
            output.status = decision["decision"]
        state.approval_decision = decision
    return state
```

**Thread lifecycle:**

```
POST /v1/threads                        → create thread_id
POST /v1/threads/{id}/runs/wait         → first message: graph runs, checkpoints saved
  ── graph may interrupt() at HITL ──
GET  /v1/threads/{id}/state             → inspect current state (pending approval)
POST /v1/threads/{id}/runs/wait         → resume with Command(resume={decision})
  ── graph resumes from checkpoint ──
GET  /v1/threads/{id}/history           → full checkpoint history (time-travel)
```

---

### 4.2 Tier 2 — Working Memory (RunContext)

**Purpose:** Typed state object that flows through the agent pipeline within a single graph execution. Accumulates evidence, tool results, and agent outputs as the graph traverses nodes. Disposed after the run completes.

**Contents:**
- Intent classification from the supervisor
- Target entity IDs (incident, problem, etc.)
- Evidence gathered by tool calls
- Agent outputs from each executor
- Critic feedback and retry metadata
- Tool call results with timing

**Lifecycle:** Created at graph entry, passed through all nodes, discarded after response is formatted. Durable artifacts (agent outputs, approval tasks) are extracted and written to the Domain Store before disposal.

```python
# app/models/agent.py

class RunContext(BaseModel):
    """Working memory — shared state within a single graph execution.

    This is the LangGraph state schema: every node reads and writes to this object.
    It is NOT persisted beyond the graph run — durable artifacts are extracted
    to the Domain Store by the response formatter node.
    """
    # Thread identity
    thread_id: str = ""
    user: CurrentUser | None = None

    # Supervisor classification
    intent: str = ""
    selected_agents: list[str] = Field(default_factory=list)
    requires_approval: bool = False

    # Message accumulation (OpenAI format — this IS the conversation)
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)

    # Agent pipeline state
    target_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    tool_results: list[ToolCallResult] = Field(default_factory=list)

    # Quality gate
    retry_count: int = 0
    max_retries: int = 2
    critic_score: float | None = None
    critic_feedback: str = ""

    # Approval gate
    approval_decision: dict[str, Any] | None = None
```

**Why `messages: Annotated[list, add_messages]`:**
The `add_messages` reducer is LangGraph's built-in message accumulator. When a node returns `{"messages": [new_msg]}`, it appends to the existing list rather than replacing it. This is how conversation history flows through the graph — each agent node sees all prior messages (system prompt + user message + prior tool calls + prior agent responses).

This replaces the KnowledgeForge2 pattern of manually formatting history as a string and injecting it into the user prompt. The LLM now receives the full native OpenAI message array.

---

### 4.3 Tier 3 — Domain Store (Application State)

**Purpose:** Persistent storage for IT operations domain data — incidents, problems, changes, knowledge articles, approvals, and audit log. Serves as the system of record for the chatbot's operational context.

**Contents:**
- ITSM records (incidents, problems, changes) — cached from ServiceNow
- Knowledge articles — cached from Azure AI Search
- Agent outputs — results of successful agent runs
- Approval tasks — HITL approval lifecycle
- Audit log — every state-changing operation
- Runtime settings — naming, personas, connector config
- Dashboard snapshots — cached aggregations

**Interface:**

```python
# app/store/base.py

class DomainStoreInterface(ABC):
    """Abstract interface for application state persistence.

    Implementations:
    - InMemoryStore: POC — dict-based, seeded with demo data
    - CosmosStore: Production — Azure Cosmos DB (MongoDB API)
    - TableStore: Alternative — Azure Table Storage (cheaper, simpler)
    """

    # --- Threads ---
    @abstractmethod
    async def add_thread(self, thread: OperationalThread) -> None: ...
    @abstractmethod
    async def get_thread(self, thread_id: str) -> OperationalThread | None: ...
    @abstractmethod
    async def list_threads(self, user_id: str | None = None) -> list[OperationalThread]: ...

    # --- Domain records ---
    @abstractmethod
    async def upsert_incident(self, record: IncidentRecord) -> None: ...
    @abstractmethod
    async def get_incident(self, incident_id: str) -> IncidentRecord | None: ...
    @abstractmethod
    async def list_incidents(self, filters: dict | None = None) -> list[IncidentRecord]: ...
    # ... same pattern for problems, changes, knowledge_articles

    # --- Agent outputs ---
    @abstractmethod
    async def add_output(self, output: AgentOutput) -> None: ...
    @abstractmethod
    async def get_outputs(self, target_id: str | None = None) -> list[AgentOutput]: ...

    # --- Approvals ---
    @abstractmethod
    async def add_approval(self, task: ApprovalTask) -> None: ...
    @abstractmethod
    async def update_approval(self, task_id: str, decision: ApprovalDecision) -> None: ...
    @abstractmethod
    async def list_approvals(self, status: str | None = None) -> list[ApprovalTask]: ...

    # --- Audit ---
    @abstractmethod
    async def log_event(self, kind: str, payload: dict) -> None: ...
    @abstractmethod
    async def get_audit_log(self, limit: int = 100) -> list[AuditEvent]: ...

    # --- Settings ---
    @abstractmethod
    async def get_settings(self) -> RuntimeSettings: ...
    @abstractmethod
    async def save_settings(self, settings: RuntimeSettings) -> None: ...

    # --- Aggregation ---
    @abstractmethod
    async def snapshot(self) -> DashboardSnapshot: ...
```

**Implementation progression:**

| Phase | Implementation | Persistence | Use Case |
|---|---|---|---|
| **POC** | `InMemoryStore` | None (seeded on startup) | Local development, demos |
| **UAT** | `CosmosStore` | Azure Cosmos DB (MongoDB API) | Shared test environment |
| **Production** | `CosmosStore` | Azure Cosmos DB (MongoDB API) | Full deployment |
| **Alt** | `TableStore` | Azure Table Storage | Cost-optimized (simpler queries) |

**Why Cosmos DB over Table Storage:**
- The target framework uses Cosmos-style store abstractions over MongoDB-compatible storage
- Rich query support (filters, aggregations, indexing) vs Table Storage's limited querying
- Same SDK family (`motor` async MongoDB driver) as comparable enterprise document-store implementations
- Cosmos DB MongoDB API supports change streams for future event-driven patterns

**Store factory:**

```python
# app/store/factory.py

async def create_domain_store(settings: Settings) -> DomainStoreInterface:
    """Create domain store based on configuration."""
    if settings.storage_backend == "cosmos":
        store = CosmosStore(
            connection_string=settings.cosmos_connection_string,
            database_name=settings.cosmos_database or "ai-ops-agent",
        )
        await store.initialize()
        return store
    if settings.storage_backend == "azure_table":
        store = TableStore(settings.azure_table_connection_string)
        await store.initialize()
        return store
    # Default: in-memory with demo data
    store = InMemoryStore()
    await store.seed()
    return store
```

---

### 4.4 Memory Tier Interaction Flow

```
HTTP Request (POST /api/chat)
  │
  ▼
┌───────────────────────────────────────────────────────┐
│ ChatService.handle(message, thread_id, user)          │
│                                                       │
│  1. Store user MessageRecord → Domain Store (Tier 3)  │
│                                                       │
│  2. Build input: {"messages": [HumanMessage(...)]}    │
│                                                       │
│  3. graph.ainvoke(                                    │
│       input,                                          │
│       config={"configurable": {                       │
│           "thread_id": thread_id   ← Tier 1 key      │
│       }}                                              │
│     )                                                 │
│     ┌─────────────────────────────────────────────┐   │
│     │ LangGraph Execution                         │   │
│     │                                             │   │
│     │ ┌── Supervisor ──┐                          │   │
│     │ │ reads messages  │ ← Tier 1 (prior turns)  │   │
│     │ │ classifies      │                         │   │
│     │ │ writes intent   │ → Tier 2 (RunContext)   │   │
│     │ └────────┬────────┘                         │   │
│     │          ▼                                  │   │
│     │ ┌── Agent Node ──┐                          │   │
│     │ │ reads context   │ ← Tier 2 (RunContext)   │   │
│     │ │ calls tools     │ → Connectors            │   │
│     │ │ appends output  │ → Tier 2 (RunContext)   │   │
│     │ └────────┬────────┘                         │   │
│     │          ▼                                  │   │
│     │ ┌── Critic ───────┐                         │   │
│     │ │ scores quality  │ ← Tier 2 (RunContext)   │   │
│     │ │ pass/retry/HITL │                         │   │
│     │ └────────┬────────┘                         │   │
│     │          ▼                                  │   │
│     │ ┌── HITL Gate ────┐                         │   │
│     │ │ interrupt()     │ → Tier 1 (checkpoint)   │   │
│     │ │ ... human ...   │                         │   │
│     │ │ resume()        │ ← Tier 1 (resume)       │   │
│     │ └────────┬────────┘                         │   │
│     │          ▼                                  │   │
│     │ ┌── Formatter ────┐                         │   │
│     │ │ extract outputs │ ← Tier 2                │   │
│     │ │ persist to store│ → Tier 3 (Domain Store) │   │
│     │ └─────────────────┘                         │   │
│     │                                             │   │
│     │ Checkpoint saved ──→ Tier 1 (per-node)      │   │
│     └─────────────────────────────────────────────┘   │
│                                                       │
│  4. Store assistant MessageRecord → Tier 3            │
│  5. Return ChatResponse to frontend                   │
└───────────────────────────────────────────────────────┘
```

---

### 4.5 Long-Term Memory (Future Extension)

Long-term memory provides cross-session knowledge storage: user preferences, learned resolution patterns, semantic search over past conversations, and agent performance baselines. Comparable enterprise frameworks often implement LangGraph's `BaseStore` for this purpose. The interface is defined for future expansion.

```python
# app/memory/long_term.py (placeholder — not implemented in POC)

from langgraph.store.base import BaseStore


class LongTermMemoryStore(BaseStore):
    """Cross-session knowledge store.

    Future implementation backed by Azure Cosmos DB (MongoDB API).
    Stores: user preferences, resolution pattern embeddings,
    learned KB article quality scores, agent performance history.

    POC: Not instantiated — interface exists for architectural completeness.
    Production: CosmosDB with TTL-based expiration on stale entries.
    """

    async def aget(self, key: str, namespace: tuple[str, ...] | None = None) -> list[dict] | None:
        raise NotImplementedError("Long-term memory not implemented in POC")

    async def aput(self, key: str, value: dict, namespace: tuple[str, ...] | None = None) -> None:
        raise NotImplementedError("Long-term memory not implemented in POC")

    async def adelete(self, key: str, namespace: tuple[str, ...] | None = None) -> None:
        raise NotImplementedError("Long-term memory not implemented in POC")

    async def abatch(self, ops) -> list:
        raise NotImplementedError("Long-term memory not implemented in POC")

    async def batch(self, ops) -> list:
        raise NotImplementedError("Long-term memory not implemented in POC")
```

When activated, long-term memory enables:
- **User preference learning**: resolution style, notification preferences, frequently accessed services
- **Resolution pattern caching**: embedding-indexed past successful resolutions → faster retrieval for similar incidents
- **KB quality scoring**: track which articles led to successful resolutions → weight future retrieval
- **Agent tuning**: per-agent performance baselines → adaptive critic thresholds

---

## 5. Orchestration Deep Dive

### 5.1 Repository Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app, lifespan, route registration
│   ├── config.py                    # pydantic-settings: all env vars
│   │
│   ├── models/                      # Pydantic models
│   │   ├── __init__.py
│   │   ├── domain.py                # IncidentRecord, ProblemRecord, ChangeRecord, KnowledgeArticle
│   │   ├── agent.py                 # RunContext (Tier 2), AgentOutput, ToolCallResult
│   │   ├── chat.py                  # OperationalThread, MessageRecord, ChatRequest, ChatResponse
│   │   ├── approval.py              # ApprovalTask, ApprovalDecision
│   │   ├── dashboard.py             # DashboardSnapshot, MetricPayload
│   │   └── auth.py                  # CurrentUser, TokenClaims
│   │
│   ├── memory/                      # ★ NEW — Memory tier management
│   │   ├── __init__.py
│   │   ├── checkpointer.py          # Tier 1: checkpointer factory (MemorySaver → Redis cascade)
│   │   └── long_term.py             # Tier 3b: LTM placeholder (BaseStore interface)
│   │
│   ├── agents/                      # LangGraph agent nodes
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseAgent: LLM reasoning loop + tool dispatch
│   │   ├── supervisor.py            # Supervisor: LLM intent classification → agent routing
│   │   ├── critic.py                # Critic: quality scoring + retry/escalation
│   │   ├── incident.py              # IncidentAgent
│   │   ├── knowledge.py             # KnowledgeAgent (RAG retrieval + gap detection)
│   │   ├── problem.py               # ProblemRcaAgent
│   │   ├── postmortem.py            # PostmortemAgent
│   │   └── governance.py            # GovernanceAgent
│   │
│   ├── tools/                       # OpenAI function-call schemas + dispatch
│   │   ├── __init__.py
│   │   ├── registry.py              # ToolRegistry: name → handler mapping
│   │   ├── schemas.py               # Tool JSON schemas (OpenAI format)
│   │   ├── itsm_tools.py            # lookup, create, update incident/problem/KA
│   │   ├── search_tools.py          # hybrid_search, get_article
│   │   ├── telemetry_tools.py       # get_signals, get_metrics
│   │   └── collaboration_tools.py   # send_teams_notification
│   │
│   ├── connectors/                  # External service clients
│   │   ├── __init__.py              # ConnectorBundle dataclass
│   │   ├── base.py                  # ConnectorBase: _live flag, health_check, fallback
│   │   ├── servicenow.py            # ServiceNowConnector (httpx → SNOW REST)
│   │   ├── azure_openai.py          # AzureOpenAIConnector (chat_completion, embed)
│   │   ├── azure_search.py          # AzureSearchConnector (hybrid_search)
│   │   └── teams.py                 # TeamsConnector (Adaptive Card via webhook)
│   │
│   ├── services/                    # Business logic
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # LangGraph graph builder + checkpointer wiring
│   │   ├── chat.py                  # Conversational handler: thread → graph → response
│   │   ├── approval.py              # Approval lifecycle: create → review → dispatch
│   │   └── dashboard.py             # Dashboard snapshot aggregation + caching
│   │
│   ├── store/                       # Tier 3: Domain state persistence
│   │   ├── __init__.py
│   │   ├── base.py                  # DomainStoreInterface (abstract)
│   │   ├── memory.py                # InMemoryStore + seed_store() for POC
│   │   ├── cosmos.py                # CosmosStore (Azure Cosmos DB MongoDB API)
│   │   ├── table.py                 # TableStore (Azure Table Storage — alt)
│   │   └── factory.py               # create_domain_store() factory
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                  # Entra ID JWT validation
│   │   └── logging.py               # Structured JSON request/response logging
│   │
│   └── routes/
│       ├── __init__.py
│       ├── chat.py                  # POST /api/chat
│       ├── threads.py               # /v1/threads CRUD + state + history
│       ├── assistants.py            # /v1/assistants
│       ├── dashboard.py             # GET /api/dashboard
│       ├── incidents.py             # GET /api/incidents/*
│       ├── approvals.py             # POST /api/approvals/{id}/decision
│       ├── settings.py              # GET/PUT /api/settings
│       └── health.py                # GET /healthz
│
├── tests/
│   ├── conftest.py
│   ├── test_chat.py
│   ├── test_orchestrator.py
│   ├── test_checkpointer.py         # ★ NEW — memory tier tests
│   ├── test_connectors.py
│   ├── test_approval.py
│   └── test_routes.py
│
├── pyproject.toml
└── .env.example
```

The `app/memory/` module owns Tier 1 (conversation checkpointing) and the long-term memory interface. The `app/store/` module owns Tier 3 (domain state). Tier 2 (working memory) is the `RunContext` model in `app/models/agent.py` — a transient per-request state object managed by LangGraph.

### 5.2 LangGraph Orchestrator

```python
# app/services/orchestrator.py

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from app.config import Settings
from app.connectors import ConnectorBundle
from app.memory.checkpointer import get_checkpointer
from app.models.agent import RunContext
from app.store.base import DomainStoreInterface

logger = logging.getLogger(__name__)


class Orchestrator:
    """LangGraph orchestrator with proper checkpointing."""

    def __init__(
        self,
        settings: Settings,
        connectors: ConnectorBundle,
        store: DomainStoreInterface,
    ):
        self.settings = settings
        self.connectors = connectors
        self.store = store
        self._graph: CompiledStateGraph | None = None

    async def initialize(self) -> None:
        """Build and compile graph with checkpointer. Called once at startup."""
        checkpointer = await get_checkpointer(self.settings)
        self._graph = self._build_graph(checkpointer)
        logger.info(
            "Orchestrator initialized with checkpointer: %s",
            type(checkpointer).__name__,
        )

    def _build_graph(self, checkpointer) -> CompiledStateGraph:
        """Build the LangGraph StateGraph."""
        graph = StateGraph(RunContext)

        # Add nodes
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("incident_agent", self._incident_node)
        graph.add_node("knowledge_agent", self._knowledge_node)
        graph.add_node("problem_agent", self._problem_node)
        graph.add_node("postmortem_agent", self._postmortem_node)
        graph.add_node("governance_agent", self._governance_node)
        graph.add_node("critic", self._critic_node)
        graph.add_node("hitl_gate", self._hitl_node)
        graph.add_node("response_formatter", self._format_node)

        # Edges
        graph.set_entry_point("supervisor")
        graph.add_conditional_edges("supervisor", self._route_to_agent)

        for agent in [
            "incident_agent", "knowledge_agent", "problem_agent",
            "postmortem_agent", "governance_agent",
        ]:
            graph.add_edge(agent, "critic")

        graph.add_conditional_edges("critic", self._route_critic)
        graph.add_edge("hitl_gate", "response_formatter")
        graph.add_edge("response_formatter", END)

        # ★ Compile WITH checkpointer — this enables Tier 1 memory
        return graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["hitl_gate"],  # pause before HITL for approval
        )

    def _route_critic(self, state: RunContext) -> str:
        """Route based on critic score: pass → HITL/format, retry → supervisor, escalate → HITL."""
        if state.critic_score is not None and state.critic_score >= 0.7:
            if any(o.requires_approval for o in state.agent_outputs):
                return "hitl_gate"
            return "response_formatter"
        if state.retry_count < state.max_retries:
            return "supervisor"  # retry with critic feedback
        return "hitl_gate"  # escalate to human

    async def run(self, message: str, thread_id: str, user: dict) -> dict[str, Any]:
        """Execute the orchestrator graph for a chat message."""
        config = {
            "configurable": {
                "thread_id": thread_id,  # ← Tier 1 key for checkpointing
            }
        }
        input_state = {
            "messages": [HumanMessage(content=message)],
            "thread_id": thread_id,
            "user": user,
        }
        result = await self._graph.ainvoke(input_state, config=config)
        return result

    async def resume(self, thread_id: str, decision: dict) -> dict[str, Any]:
        """Resume graph execution after HITL approval decision."""
        config = {"configurable": {"thread_id": thread_id}}
        result = await self._graph.ainvoke(
            Command(resume=decision),
            config=config,
        )
        return result

    async def get_thread_state(self, thread_id: str) -> dict:
        """Inspect current graph state for a thread (pending approvals, etc.)."""
        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)
        return state

    # --- Node implementations (stubs — filled during implementation) ---

    async def _supervisor_node(self, state: RunContext) -> dict: ...
    async def _incident_node(self, state: RunContext) -> dict: ...
    async def _knowledge_node(self, state: RunContext) -> dict: ...
    async def _problem_node(self, state: RunContext) -> dict: ...
    async def _postmortem_node(self, state: RunContext) -> dict: ...
    async def _governance_node(self, state: RunContext) -> dict: ...
    async def _critic_node(self, state: RunContext) -> dict: ...
    async def _hitl_node(self, state: RunContext) -> dict: ...
    async def _format_node(self, state: RunContext) -> dict: ...
    def _route_to_agent(self, state: RunContext) -> str: ...
```

---

### 5.3 Application Entry Point (Lifespan)

```python
# app/main.py

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.connectors import build_connectors
from app.services.orchestrator import Orchestrator
from app.store.factory import create_domain_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()

    # Tier 3: Domain store
    store = await create_domain_store(settings)
    logger.info("Domain store initialized: %s", type(store).__name__)

    # Connectors
    connectors = build_connectors(settings, store)

    # Orchestrator (includes Tier 1 checkpointer initialization)
    orchestrator = Orchestrator(settings, connectors, store)
    await orchestrator.initialize()

    # Attach to app state
    app.state.settings = settings
    app.state.store = store
    app.state.connectors = connectors
    app.state.orchestrator = orchestrator

    yield

    # Cleanup
    logger.info("Shutting down — cleaning up resources")


app = FastAPI(
    title="AI Operations Concierge",
    version="1.0.0",
    lifespan=lifespan,
)
```

---

## 6. Agent Architecture

### 6.1 BaseAgent Contract

Each agent implements a ReAct reasoning loop: reason → tool call → observe → repeat. Aligned with a role-based agent workflow pattern — each agent runs an LLM tool-calling loop, accumulates results in `RunContext` (Tier 2), and returns a dict update for LangGraph state.

```python
# app/agents/base.py

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.connectors.azure_openai import AzureOpenAIConnector
from app.models.agent import AgentOutput, RunContext, ToolCallResult
from app.tools.registry import ToolRegistry


class BaseAgent(ABC):
    """Abstract agent with ReAct reasoning loop.

    Aligned with a reusable base-agent pattern:
    - Each agent runs an LLM tool-calling loop
    - Tools are invoked via OpenAI function-call schemas
    - Results accumulated in RunContext (Tier 2 working memory)
    - Agent returns dict update for LangGraph state

    Framework alignment notes:
    - Comparable frameworks compile each agent as its own sub-graph via a workflow builder
    - Our agents are simpler: each is a single node function
    - Migration path: wrap node function in a role-playing agent abstraction
    """

    MAX_STEPS = 5

    def __init__(
        self,
        agent_id: str,
        llm: AzureOpenAIConnector,
        tool_registry: ToolRegistry,
        tool_names: list[str],
    ):
        self.agent_id = agent_id
        self.llm = llm
        self.tool_registry = tool_registry
        self.tool_schemas = tool_registry.get_schemas(tool_names)
        self.logger = logging.getLogger(f"agents.{agent_id}")

    async def run(self, state: RunContext) -> dict[str, Any]:
        """Execute ReAct loop: reason → tool_call → observe → repeat.

        Returns a dict of state updates for LangGraph (not a full RunContext).
        """
        messages = self._build_messages(state)

        for step in range(self.MAX_STEPS):
            response = await self.llm.chat_completion(
                messages=messages,
                tools=self.tool_schemas,
                temperature=0.2,
            )

            if response.tool_calls:
                # Act: execute tool calls
                messages.append(response)
                for call in response.tool_calls:
                    result = await self.tool_registry.execute(
                        call.function.name,
                        json.loads(call.function.arguments),
                    )
                    tool_result = ToolCallResult(
                        tool_name=call.function.name,
                        arguments=json.loads(call.function.arguments),
                        result=result,
                        duration_ms=0,  # TODO: measure
                    )
                    messages.append(
                        ToolMessage(content=json.dumps(result), tool_call_id=call.id)
                    )
                    state.tool_results.append(tool_result)
            else:
                # Observe: agent has finished reasoning
                output = self._parse_output(response, state)
                return {
                    "agent_outputs": [output],
                    "evidence": state.evidence,
                    "tool_results": state.tool_results,
                    "messages": messages,
                }

        # Max steps reached — return partial output
        return self._fallback_output(state)

    @abstractmethod
    def _build_messages(self, state: RunContext) -> list[dict]:
        """Build the message array for LLM (system prompt + context)."""
        ...

    @abstractmethod
    def _parse_output(self, response: Any, state: RunContext) -> AgentOutput:
        """Parse LLM response into a structured AgentOutput."""
        ...

    def _fallback_output(self, state: RunContext) -> dict:
        """Return a low-confidence output when max steps exceeded."""
        return {
            "agent_outputs": [
                AgentOutput(
                    agent_id=self.agent_id,
                    target_type="platform",
                    target_id="",
                    title=f"{self.agent_id} reached max reasoning steps",
                    summary="Agent could not reach a conclusion within the step limit.",
                    confidence=0.0,
                    requires_approval=True,
                )
            ],
        }
```

### 6.2 Agent Composition — Framework Migration Pattern

Comparable enterprise agent frameworks use a supervisor agent with sub-agent registration and binding tools for agent handoff. The POC uses flat nodes with conditional edges. The migration path wraps each node function in a role-playing agent abstraction:

```python
# Future: framework-style composition (not POC)
# Each agent becomes a role-playing agent with its own sub-graph
# Supervisor uses binding tools to route via Command(goto=Send(...))

from framework_sdk.prebuilt.agents import SupervisorAgent, RolePlayingAgent

incident_agent = RolePlayingAgent(
    agent_name="incident_agent",
    tools=[lookup_incident, create_incident, update_incident],
    prompt_elements=incident_prompt,
    chat_model_config=azure_openai_config,
)

supervisor = SupervisorAgent(
    agent_name="supervisor",
    sub_agents=[incident_agent, knowledge_agent, problem_agent],
    prompt_elements=supervisor_prompt,
    chat_model_config=azure_openai_config,
)

# Returns CompiledStateGraph — register in flows.json
graph = supervisor.workflow
```

---

## 7. Data Architecture

### 7.1 Connector Layer

All connectors are async-first and implement the `ConnectorBase` pattern with `_live` fallback:

```python
# app/connectors/base.py

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel


class ConnectorHealth(BaseModel):
    """Health check result for a connector."""
    connected: bool
    source: str       # "live" | "fallback"
    latency_ms: int | None = None
    error: str | None = None


class ConnectorBase(ABC):
    """Base class for external service connectors.

    Design principles:
    1. _live flag: toggled by health check or config presence
    2. Graceful degradation: fallback to in-memory data when _live=False
    3. Async-first: all I/O methods are async
    4. Lazy initialization: clients built on first use (not constructor)
    """

    def __init__(self, settings):
        self._live: bool = False
        self._settings = settings
        self.logger = logging.getLogger(f"connectors.{self.__class__.__name__}")

    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        """Probe external service availability."""
        ...

    def _require_live(self, operation: str) -> bool:
        """Check if connector is live. Log warning and return False if not."""
        if not self._live:
            self.logger.warning(
                "Connector offline — using fallback",
                extra={"operation": operation},
            )
        return self._live
```

### 7.2 Azure OpenAI Connector

```python
# app/connectors/azure_openai.py

from __future__ import annotations

from openai import AsyncAzureOpenAI

from app.connectors.base import ConnectorBase, ConnectorHealth


class AzureOpenAIConnector(ConnectorBase):
    """Azure OpenAI connector for chat completion and embeddings.

    Chat: gpt-5.3-chat (temperature 0.2 for agent reasoning, 0.7 for conversational)
    Embeddings: text-embedding-3-large (3072 dimensions)
    """

    def __init__(self, settings):
        super().__init__(settings)
        self._client: AsyncAzureOpenAI | None = None
        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            self._live = True

    async def chat_completion(self, messages, tools=None, temperature=0.2):
        """Call Azure OpenAI chat completions with optional function calling."""
        if not self._require_live("chat_completion"):
            return self._fallback_chat(messages)
        return await self._client.chat.completions.create(
            model=self._settings.azure_openai_chat_deployment,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector."""
        if not self._require_live("embed"):
            return [0.0] * 3072  # fallback: zero vector
        response = await self._client.embeddings.create(
            input=text,
            model=self._settings.azure_openai_embedding_deployment,
        )
        return response.data[0].embedding

    async def health_check(self) -> ConnectorHealth:
        if not self._client:
            return ConnectorHealth(connected=False, source="fallback", error="Not configured")
        try:
            await self._client.models.list()
            return ConnectorHealth(connected=True, source="live")
        except Exception as e:
            return ConnectorHealth(connected=False, source="fallback", error=str(e))
```

---

### 7.3 Application Configuration

```python
# app/config.py

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration — all values from environment variables."""

    # --- ServiceNow ---
    snow_instance_url: str = ""
    snow_svc_username: str = ""
    snow_svc_password: str = ""

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = "gpt-5.3-chat"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2025-01-01"

    # --- Azure AI Search ---
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index: str = "ai-ops-knowledge-index"

    # --- Entra ID ---
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    auth_disabled: bool = False

    # --- Teams ---
    teams_webhook_url: str = ""

    # --- Memory Tier 1: Conversation checkpointing ---
    redis_url: str = ""
    # Format: rediss://:password@hostname:6380/0 (Azure Cache for Redis, SSL)
    # Empty = MemorySaver fallback (POC)

    # --- Memory Tier 3: Domain store ---
    storage_backend: str = "memory"
    # "memory" = InMemoryStore (POC)
    # "cosmos"  = Azure Cosmos DB MongoDB API
    # "azure_table" = Azure Table Storage (simpler/cheaper alternative)
    cosmos_connection_string: str = ""
    cosmos_database: str = "ai-ops-agent"
    azure_table_connection_string: str = ""

    # --- Application ---
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "case_sensitive": False}
```

---

### 7.4 Dependencies

Core install requires `MemorySaver` + `InMemoryStore` with zero external services. Production adds services via pip extras.

```toml
# backend/pyproject.toml

[project]
name = "ai-ops-agent"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    # --- Web framework ---
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",

    # --- LLM & Orchestration ---
    "openai>=1.30",
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "langchain-openai>=0.2",

    # --- Azure Services ---
    "azure-search-documents>=11.4",     # AI Search (hybrid search)
    "azure-data-tables>=12.5",          # Table Storage (alt store)

    # --- Auth ---
    "python-jose[cryptography]>=3.3",   # JWT validation

    # --- Memory Tier 1 (conversation checkpointing) ---
    # MemorySaver is built into langgraph (no extra dep)
    # Redis checkpointer added as optional for production:
]

[project.optional-dependencies]
redis = [
    "langgraph-checkpoint-redis>=2.0",  # AsyncRedisSaver for Tier 1
    "redis>=5.0",                       # Redis client
]
cosmos = [
    "motor>=3.3",                       # Async MongoDB driver for Cosmos DB
    "pymongo>=4.6",                     # MongoDB driver
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
]
all = [
    "ai-ops-agent[redis,cosmos,dev]",
]
```

**Optional Dependency Groups:**

| Group | Purpose | Packages |
|-------|---------|----------|
| `[redis]` | Tier 1 production checkpointing | `langgraph-checkpoint-redis`, `redis` |
| `[cosmos]` | Tier 3 production domain store | `motor`, `pymongo` |
| `[dev]` | Development tooling | `pytest`, `pytest-asyncio`, `ruff`, `mypy` |
| `[all]` | Everything | `[redis,cosmos,dev]` |

---

### 7.5 Observability

```python
# app/observability/__init__.py (placeholder — implemented in later phase)

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def setup_observability() -> None:
    """Initialize observability stack.

    Phase 1 (POC): Application Insights via OpenCensus/OpenTelemetry
    Phase 2+: LangChain tracing via LangSmith or Arize Phoenix

    Comparable enterprise frameworks often pair production tracing with a lighter-weight local tracing stack.
    Our stack uses Application Insights as primary (Azure-native) with optional
    Phoenix/LangSmith for LLM-specific tracing.
    """
    app_insights_conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if app_insights_conn:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanExporter
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            exporter = AzureMonitorTraceExporter(connection_string=app_insights_conn)
            provider = TracerProvider()
            provider.add_span_processor(BatchSpanExporter(exporter))
            trace.set_tracer_provider(provider)
            logger.info("Application Insights tracing enabled")
        except ImportError:
            logger.info("Azure Monitor exporter not installed — tracing disabled")
    else:
        logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set — tracing disabled")
```

---

## 8. Infrastructure

### 8.1 Azure Cache for Redis (Tier 1 — Production Checkpointing)

```hcl
# infra/modules/redis/main.tf

resource "azurerm_redis_cache" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  capacity            = 0          # C0 (250MB) — sufficient for checkpoints
  family              = "C"
  sku_name            = "Basic"    # POC — upgrade to Standard for replication
  non_ssl_port_enabled = false
  minimum_tls_version = "1.2"
  tags                = var.tags
}

output "hostname" {
  value = azurerm_redis_cache.this.hostname
}

output "primary_key" {
  value     = azurerm_redis_cache.this.primary_access_key
  sensitive = true
}

output "connection_string" {
  value     = "rediss://:${azurerm_redis_cache.this.primary_access_key}@${azurerm_redis_cache.this.hostname}:6380/0"
  sensitive = true
}
```

### 8.2 Azure Cosmos DB (Tier 3 — Production Domain Store)

```hcl
# infra/modules/cosmos/main.tf

resource "azurerm_cosmosdb_account" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  offer_type          = "Standard"
  kind                = "MongoDB"
  tags                = var.tags

  # Free tier eligible for one account per subscription
  free_tier_enabled = var.environment == "dev" ? true : false

  consistency_policy {
    consistency_level = "Session"  # sufficient for single-region chatbot
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  capabilities {
    name = "EnableMongo"
  }

  capabilities {
    name = "EnableServerless"  # serverless = pay-per-request (cost-effective for POC)
  }
}

resource "azurerm_cosmosdb_mongo_database" "this" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

output "connection_string" {
  value     = azurerm_cosmosdb_account.this.primary_mongodb_connection_string
  sensitive = true
}

output "endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}
```

### 8.3 Root Module Integration

```hcl
# Add to infra/main.tf:

module "redis" {
  source              = "./modules/redis"
  name                = "redis-ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.location
  tags                = var.tags
}

module "cosmos" {
  source              = "./modules/cosmos"
  name                = "cosmos-ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.location
  database_name       = "ai-ops-agent"
  environment         = var.environment
  tags                = var.tags
}

# Update app_service module app_settings:
module "app_service" {
  # ... existing config ...
  app_settings = {
    # ... existing settings ...
    REDIS_URL                     = module.redis.connection_string
    STORAGE_BACKEND               = "cosmos"
    COSMOS_CONNECTION_STRING       = module.cosmos.connection_string
    COSMOS_DATABASE               = "ai-ops-agent"
  }
}
```

---

## 9. Framework Migration Path

This architecture minimizes friction when migrating to a target enterprise agentic framework:

| Our Component | Target Framework Equivalent | Migration Effort |
|---|---|---|
| `BaseAgent` (node functions) | `RolePlayingAgent.build_workflow()` | Wrap node logic in `RolePlayingAgent`, move to `sub_agents` |
| `Orchestrator._build_graph()` | `SupervisorAgent.build_workflow()` | Replace manual graph building with `SupervisorAgent` composition |
| `get_checkpointer()` cascade | flow-controller priority resolution | Direct alignment — same priority cascade |
| `ToolRegistry` | `BaseTools(ToolNode)` | Adopt LangChain `@tool` decorator, drop custom schemas |
| `ConnectorBundle` | `RunnableConfig["configurable"]` | Move connector config to `configurable` dict |
| `DomainStoreInterface` | Cosmos-style store abstraction (LangGraph `BaseStore`) | Adapt interface methods to `aget/aput/adelete` |
| `InMemoryStore` | N/A (not needed in target framework production) | Remove — target framework uses live connectors |
| `RunContext` | `MessagesState` + custom fields | Map custom fields to the target framework state schema |
| Routes (`/api/*`) | framework-managed flow endpoints | Wrap routes behind the target framework registry API |
| Auth (Entra ID JWT) | IPA auth (`ipa.auth`) | Replace JWT validation with IPA dependency injection |

**The connector layer (ServiceNow, Azure AI Search, Azure OpenAI) transfers directly — only the framework runtime changes.**

---

## 10. Appendices

### 10.1 Environment Variable Reference

| Variable | Required | Phase | Tier | Used By |
|---|---|---|---|---|
| `REDIS_URL` | No (POC) / Yes (Prod) | 2+ | Tier 1 | Checkpointer factory |
| `STORAGE_BACKEND` | No (defaults to "memory") | 1 | Tier 3 | Domain store factory |
| `COSMOS_CONNECTION_STRING` | No (POC) / Yes (Prod) | 2+ | Tier 3 | CosmosStore |
| `COSMOS_DATABASE` | No (defaults to "ai-ops-agent") | 2+ | Tier 3 | CosmosStore |
| `AZURE_TABLE_CONNECTION_STRING` | No | Alt | Tier 3 | TableStore |
| `SNOW_INSTANCE_URL` | Yes (live) | 1 | — | ServiceNowConnector |
| `SNOW_SVC_USERNAME` | Yes (live) | 1 | — | ServiceNowConnector |
| `SNOW_SVC_PASSWORD` | Yes (live) | 1 | — | ServiceNowConnector |
| `AZURE_OPENAI_ENDPOINT` | Yes | 1 | — | AzureOpenAIConnector |
| `AZURE_OPENAI_API_KEY` | Yes | 1 | — | AzureOpenAIConnector |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Yes | 1 | — | AzureOpenAIConnector |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Yes | 1 | — | AzureOpenAIConnector |
| `AZURE_OPENAI_API_VERSION` | Yes | 1 | — | AzureOpenAIConnector |
| `AZURE_SEARCH_ENDPOINT` | Yes | 1 | — | AzureSearchConnector |
| `AZURE_SEARCH_API_KEY` | Yes | 1 | — | AzureSearchConnector |
| `AZURE_SEARCH_INDEX` | Yes | 1 | — | AzureSearchConnector |
| `ENTRA_TENANT_ID` | Yes | 2 | — | Auth middleware |
| `ENTRA_CLIENT_ID` | Yes | 2 | — | Auth middleware |
| `AUTH_DISABLED` | Dev only | 1 | — | Auth middleware |
| `TEAMS_WEBHOOK_URL` | Optional | 2 | — | TeamsConnector |
| `LOG_LEVEL` | Optional | 1 | — | Logging config |
| `CORS_ORIGINS` | Optional | 1 | — | CORS middleware |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | 1 | — | Observability |

---

### 10.2 Glossary

| Term | Definition |
|------|------------|
| **HITL** | Human-in-the-Loop — approval pattern where agents pause for human review |
| **ITSM** | IT Service Management — ServiceNow platform for incident/change management |
| **MTTR** | Mean Time To Resolution — average time to resolve an incident |
| **RAG** | Retrieval Augmented Generation — LLM with external document retrieval |
| **ReAct** | Reasoning + Acting — agent loop pattern (reason → tool call → observe → repeat) |
| **RunContext** | LangGraph state schema carrying working memory through a graph execution |
| **Checkpointer** | LangGraph persistence backend for saving/resuming graph state |
| **Target framework** | Enterprise agentic workflow framework used by the destination runtime |

### 10.3 Decision Log

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| **3-tier memory** over single store | Industry standard for AI agent systems. Separates concerns by lifecycle and access pattern. Aligns with common short-term plus durable-store patterns. | Single `MemoryStore` (rejected: conflates transient and durable state) |
| **LangGraph `MemorySaver`** for POC checkpointing | Zero-dependency, built into LangGraph. Sufficient for single-process POC. | SQLite checkpointer (unnecessary complexity for POC), Redis from day 1 (over-engineering for dev) |
| **`AsyncRedisSaver`** for production checkpointing | Uses a standard LangGraph-compatible Redis checkpointer. Azure Cache for Redis is managed, SSL-enabled, sub-ms latency. | Postgres checkpointer (no Postgres in our Azure stack), custom implementation (maintenance burden) |
| **Cosmos DB MongoDB API** for domain store | Aligns with Cosmos-style document collections over the Motor async MongoDB driver. Rich queries, change streams, serverless billing for POC. | Azure Table Storage (cheaper but limited queries), Azure SQL (overkill for document-oriented data) |
| **`RunContext` as LangGraph state schema** | Working memory lives inside the graph execution. No separate persistence needed — LangGraph checkpoints cover it. | Separate working memory store (unnecessary — graph state IS working memory) |
| **`interrupt_before=["hitl_gate"]`** for approvals | LangGraph's native HITL pattern. Pauses execution, saves checkpoint, resumes on human input. | Manual polling (more code, less reliable), WebSocket push (complexity, no LangGraph native support) |
| **Optional deps** (`[redis]`, `[cosmos]`) | POC runs with zero external services. Production adds via pip extras. Follows a common pattern of optional heavy dependencies. | All deps required (breaks local dev), runtime feature flags (less explicit) |

### 10.4 Related Documents

| Document | Location | Content |
|----------|----------|---------|
| **Backend Services Specification** | [BACKEND-SERVICES.md](BACKEND-SERVICES.md) | TSD Part 2 — per-module service specifications |
| **Frontend Architecture** | [frontend/docs/architecture/FRONTEND-ARCHITECTURE.md](../../../frontend/docs/architecture/FRONTEND-ARCHITECTURE.md) | Frontend architecture overview |
| **Frontend Component Reference** | [frontend/docs/architecture/COMPONENT-REFERENCE.md](../../../frontend/docs/architecture/COMPONENT-REFERENCE.md) | Component specifications |

---

**END OF TSD PART 1 — BACKEND OVERVIEW & ARCHITECTURE**
