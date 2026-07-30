# Technical Solution Document (TSD) — Part 2

## SwiftAssist AI · Backend Services
## Service Specifications

**Version:** 1.0  
**Date:** April 28, 2026  
**Author:** AI Operations Concierge Team  
**Classification:** Internal Use — Enterprise IT Operations

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-28 | CM Sarte | Initial services specification |

---

## Table of Contents

1. [Services Overview](#1-services-overview)
2. [Service 1: Orchestrator](#2-service-1-orchestrator)
3. [Service 2: Chat Service](#3-service-2-chat-service)
4. [Service 3: Agent Layer](#4-service-3-agent-layer)
5. [Service 4: Tool Layer](#5-service-4-tool-layer)
6. [Service 5: Connector Layer](#6-service-5-connector-layer)
7. [Service 6: Store Layer](#7-service-6-store-layer)
8. [Service 7: Memory Layer](#8-service-7-memory-layer)
9. [Middleware](#9-middleware)
10. [API Routes](#10-api-routes)
11. [Cross-Cutting Concerns](#11-cross-cutting-concerns)
12. [Appendices](#12-appendices)

---

## 1. Services Overview

### 1.1 Service Inventory

| Module | Responsibility | Key Dependencies | Location |
|--------|----------------|------------------|----------|
| **Orchestrator** | LangGraph graph building, checkpointer wiring, execution | LangGraph, agents, memory, connectors | `app/services/orchestrator.py` |
| **Chat Service** | Thread management, message handling, graph invocation | Orchestrator, Domain Store | `app/services/chat.py` |
| **Agent Layer** | LLM reasoning loops, tool dispatch, output generation | AzureOpenAI, ToolRegistry | `app/agents/` |
| **Tool Layer** | OpenAI function-call schemas, tool dispatch registry | Connectors | `app/tools/` |
| **Connector Layer** | External service clients with live/fallback modes | httpx, openai, azure SDKs | `app/connectors/` |
| **Store Layer** | Domain state persistence (Tier 3) | Pydantic models | `app/store/` |
| **Memory Layer** | Conversation checkpointing (Tier 1), LTM placeholder | LangGraph checkpointers | `app/memory/` |
| **Middleware** | Auth (Entra ID JWT), structured logging | python-jose | `app/middleware/` |
| **API Routes** | FastAPI routers for HTTP endpoints | All services | `app/routes/` |

### 1.2 Common Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | ≥ 0.115 | Web framework |
| Pydantic | v2 | Data validation, settings |
| LangGraph | ≥ 0.2 | Agent orchestration |
| LangChain Core | ≥ 0.3 | Message types, runnables |
| OpenAI SDK | ≥ 1.30 | Azure OpenAI client |
| httpx | ≥ 0.27 | Async HTTP client |
| uvicorn | ≥ 0.30 | ASGI server |

### 1.3 Architectural Patterns

#### Dependency Injection

All services are injected into route handlers via FastAPI's `Depends()` and `request.app.state`:

```python
from fastapi import Request, Depends

async def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator

async def get_store(request: Request) -> DomainStoreInterface:
    return request.app.state.store

@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
):
    ...
```

#### Connector Fallback Pattern

Every connector implements the `_live` flag pattern:

```python
class ConnectorBase(ABC):
    def __init__(self, settings):
        self._live: bool = False
        self._settings = settings

    def _require_live(self, operation: str) -> bool:
        if not self._live:
            self.logger.warning("Connector offline — using fallback", extra={"operation": operation})
        return self._live

    @abstractmethod
    async def health_check(self) -> ConnectorHealth: ...
```

#### Error Handling

All exceptions flow through centralized handlers in `main.py`:

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(KeyError)
async def key_error_handler(request, exc):
    return JSONResponse(status_code=404, content={"error": f"Not found: {exc}"})
```

---

## 2. Service 1: Orchestrator

### 2.1 Overview

**Module:** `app/services/orchestrator.py`  
**Responsibility:** Build and compile the LangGraph `StateGraph`, wire checkpointer, execute graph runs, handle HITL resume

### 2.2 Interface

```python
class Orchestrator:
    async def initialize(self) -> None:
        """Build and compile graph with checkpointer. Called once at startup."""

    async def run(self, message: str, thread_id: str, user: dict) -> dict[str, Any]:
        """Execute graph for a chat message. Returns final RunContext state."""

    async def resume(self, thread_id: str, decision: dict) -> dict[str, Any]:
        """Resume graph after HITL approval decision."""

    async def get_thread_state(self, thread_id: str) -> dict:
        """Inspect current graph state (pending approvals, checkpoint)."""
```

### 2.3 Graph Topology

```
┌──────────────┐
│  ENTRY       │
│  supervisor  │──── intent classification (LLM)
└──────┬───────┘
       │ conditional_edges(_route_to_agent)
       ▼
┌──────────────────────────────────────────┐
│  EXECUTOR NODES (one per agent type)      │
│  ├── incident_agent                       │
│  ├── knowledge_agent                      │
│  ├── problem_agent                        │
│  ├── postmortem_agent                     │
│  └── governance_agent                     │
└──────────────┬───────────────────────────┘
               │ edge → critic
               ▼
┌──────────────┐
│  critic      │──── quality scoring (LLM)
└──────┬───────┘
       │ conditional_edges(_route_critic)
       │
       ├── score ≥ 0.7 + no approval → response_formatter → END
       ├── score ≥ 0.7 + approval needed → hitl_gate → response_formatter → END
       ├── retry_count < max → supervisor (retry with feedback)
       └── max retries reached → hitl_gate (escalate to human)
```

### 2.4 Compilation

```python
def _build_graph(self, checkpointer) -> CompiledStateGraph:
    graph = StateGraph(RunContext)

    graph.add_node("supervisor", self._supervisor_node)
    graph.add_node("incident_agent", self._incident_node)
    graph.add_node("knowledge_agent", self._knowledge_node)
    graph.add_node("problem_agent", self._problem_node)
    graph.add_node("postmortem_agent", self._postmortem_node)
    graph.add_node("governance_agent", self._governance_node)
    graph.add_node("critic", self._critic_node)
    graph.add_node("hitl_gate", self._hitl_node)
    graph.add_node("response_formatter", self._format_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", self._route_to_agent)

    for agent in ["incident_agent", "knowledge_agent", "problem_agent",
                   "postmortem_agent", "governance_agent"]:
        graph.add_edge(agent, "critic")

    graph.add_conditional_edges("critic", self._route_critic)
    graph.add_edge("hitl_gate", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_gate"],
    )
```

### 2.5 Execution Flow

```python
async def run(self, message: str, thread_id: str, user: dict) -> dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "messages": [HumanMessage(content=message)],
        "thread_id": thread_id,
        "user": user,
    }
    return await self._graph.ainvoke(input_state, config=config)

async def resume(self, thread_id: str, decision: dict) -> dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    return await self._graph.ainvoke(Command(resume=decision), config=config)
```

### 2.6 Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `interrupt_before` | `["hitl_gate"]` | Nodes before which the graph pauses for HITL |
| `checkpointer` | Resolved via priority cascade | Conversation memory backend |

### 2.7 Dependencies

- `langgraph` — `StateGraph`, `CompiledStateGraph`, `END`, `Command`, `interrupt`
- `langchain-core` — `HumanMessage`, `AnyMessage`
- `app.memory.checkpointer` — `get_checkpointer()`
- `app.models.agent` — `RunContext`
- `app.connectors` — `ConnectorBundle`
- `app.store.base` — `DomainStoreInterface`

---

## 3. Service 2: Chat Service

### 3.1 Overview

**Module:** `app/services/chat.py`  
**Responsibility:** Receive user messages, manage threads, invoke orchestrator, format responses

### 3.2 Interface

```python
class ChatService:
    async def handle(self, message: str, thread_id: str, user: CurrentUser) -> ChatResponse:
        """Process a user message through the agent pipeline."""

    async def get_history(self, thread_id: str) -> list[MessageRecord]:
        """Retrieve conversation history for a thread."""
```

### 3.3 Processing Flow

```
1. Store user MessageRecord → Domain Store (Tier 3)
2. Build input: {"messages": [HumanMessage(content=message)]}
3. Invoke orchestrator.run(message, thread_id, user)
   └── LangGraph execution (Supervisor → Agent → Critic → HITL → Formatter)
4. Extract result from RunContext
5. Store assistant MessageRecord → Domain Store (Tier 3)
6. Return ChatResponse to frontend
```

### 3.4 Response Model

```python
class ChatResponse(BaseModel):
    thread_id: str
    message: str
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    pending_approvals: list[ApprovalTask] = Field(default_factory=list)
    timestamp: str
```

### 3.5 Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_history` | 20 | Maximum messages passed to LLM context |
| `default_temperature` | 0.7 | Temperature for conversational responses |

---

## 4. Service 3: Agent Layer

### 4.1 Overview

**Module:** `app/agents/`  
**Responsibility:** LLM-powered reasoning agents implementing the ReAct (Reason + Act) pattern

### 4.2 BaseAgent

**File:** `app/agents/base.py`

Abstract base class defining the ReAct reasoning loop:

```python
class BaseAgent(ABC):
    MAX_STEPS = 5

    def __init__(self, agent_id: str, llm: AzureOpenAIConnector,
                 tool_registry: ToolRegistry, tool_names: list[str]):
        self.agent_id = agent_id
        self.llm = llm
        self.tool_registry = tool_registry
        self.tool_schemas = tool_registry.get_schemas(tool_names)

    async def run(self, state: RunContext) -> dict[str, Any]:
        """Execute ReAct loop: reason → tool_call → observe → repeat."""

    @abstractmethod
    def _build_messages(self, state: RunContext) -> list[dict]:
        """Build message array for LLM (system prompt + context)."""

    @abstractmethod
    def _parse_output(self, response: Any, state: RunContext) -> AgentOutput:
        """Parse LLM response into structured AgentOutput."""
```

**Execution steps:**
1. Build messages from `RunContext` (system prompt + conversation history + evidence)
2. Call `AzureOpenAIConnector.chat_completion()` with tool schemas
3. If tool calls returned: execute via `ToolRegistry`, append results, loop
4. If final response: parse into `AgentOutput`, return state update dict
5. If max steps exceeded: return low-confidence fallback output

### 4.3 Agent Inventory

| Agent | File | Tools | Output Type |
|-------|------|-------|-------------|
| **Supervisor** | `supervisor.py` | None (classification only) | Intent + agent routing |
| **IncidentAgent** | `incident.py` | `lookup_incident`, `create_incident`, `update_incident` | Triage + resolution draft |
| **KnowledgeAgent** | `knowledge.py` | `hybrid_search`, `get_article` | KB retrieval + gap detection |
| **ProblemRcaAgent** | `problem.py` | `lookup_incident`, `get_signals` | RCA + corrective action plan |
| **PostmortemAgent** | `postmortem.py` | `lookup_incident`, `get_article` | Postmortem + review agenda |
| **GovernanceAgent** | `governance.py` | `get_metrics`, `get_signals` | Alert governance draft |
| **Critic** | `critic.py` | None (scoring only) | Quality score + feedback |

### 4.4 Supervisor Node

**Responsibility:** Classify user intent via LLM and route to appropriate executor agent.

```python
async def _supervisor_node(self, state: RunContext) -> dict:
    """LLM intent classification → agent selection."""
    response = await self.llm.chat_completion(
        messages=[
            {"role": "system", "content": SUPERVISOR_PROMPT},
            *state.messages,
        ],
        temperature=0.2,
    )
    classification = parse_supervisor_response(response)
    return {
        "intent": classification.intent,
        "selected_agents": classification.agents,
        "requires_approval": classification.requires_approval,
    }
```

**Routing decisions:**

| Intent | Routed To | Requires Approval |
|--------|-----------|-------------------|
| `triage_incident` | `incident_agent` | Yes (creates/updates SNOW) |
| `search_knowledge` | `knowledge_agent` | No (read-only) |
| `analyze_problem` | `problem_agent` | Yes (creates RCA) |
| `generate_postmortem` | `postmortem_agent` | Yes (creates PM) |
| `review_governance` | `governance_agent` | Yes (changes alert rules) |
| `general_chat` | Direct response (no agent) | No |

### 4.5 Critic Node

**Responsibility:** Score agent output quality and decide: pass, retry, or escalate.

```python
async def _critic_node(self, state: RunContext) -> dict:
    """Quality scoring via LLM."""
    response = await self.llm.chat_completion(
        messages=[
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": format_outputs_for_review(state.agent_outputs)},
        ],
        temperature=0.2,
    )
    score = parse_critic_score(response)
    return {
        "critic_score": score.score,
        "critic_feedback": score.feedback,
        "retry_count": state.retry_count + (1 if score.score < 0.7 else 0),
    }
```

**Routing logic:**

| Condition | Action |
|-----------|--------|
| Score ≥ 0.7, no approval needed | → `response_formatter` → END |
| Score ≥ 0.7, approval required | → `hitl_gate` → `response_formatter` → END |
| Score < 0.7, retries available | → `supervisor` (retry with critic feedback) |
| Score < 0.7, max retries reached | → `hitl_gate` (escalate to human) |

### 4.6 HITL Gate Node

**Responsibility:** Pause execution for human approval using LangGraph `interrupt()`.

```python
from langgraph.types import interrupt

async def _hitl_node(self, state: RunContext) -> dict:
    pending = [o for o in state.agent_outputs if o.requires_approval]
    if pending:
        decision = interrupt({
            "type": "approval_required",
            "outputs": [o.model_dump() for o in pending],
        })
        for output in pending:
            output.status = decision["decision"]
        return {"approval_decision": decision}
    return {}
```

**Resume flow:**
```
POST /v1/threads/{id}/runs/wait
Body: Command(resume={"decision": "approved", "reviewer": "user@pg.com"})
→ Graph resumes from checkpoint, HITL node returns, → response_formatter → END
```

---

## 5. Service 4: Tool Layer

### 5.1 Overview

**Module:** `app/tools/`  
**Responsibility:** Define OpenAI function-call schemas, maintain tool registry, dispatch tool execution

### 5.2 Tool Registry

**File:** `app/tools/registry.py`

```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: dict[str, dict] = {}

    def register(self, name: str, handler: Callable, schema: dict) -> None:
        self._tools[name] = handler
        self._schemas[name] = schema

    def get_schemas(self, tool_names: list[str]) -> list[dict]:
        return [self._schemas[n] for n in tool_names if n in self._schemas]

    async def execute(self, name: str, arguments: dict) -> Any:
        handler = self._tools[name]
        return await handler(**arguments)
```

### 5.3 Tool Inventory

| Tool | Module | Connector | Description |
|------|--------|-----------|-------------|
| `lookup_incident` | `itsm_tools.py` | ServiceNow | Look up incident by number or sys_id |
| `create_incident` | `itsm_tools.py` | ServiceNow | Create new incident record |
| `update_incident` | `itsm_tools.py` | ServiceNow | Update incident fields |
| `hybrid_search` | `search_tools.py` | Azure AI Search | BM25 + vector search over KB index |
| `get_article` | `search_tools.py` | Azure AI Search | Retrieve full KB article by ID |
| `get_signals` | `telemetry_tools.py` | Telemetry | Query monitoring signals/alerts |
| `get_metrics` | `telemetry_tools.py` | Telemetry | Query performance metrics |
| `send_teams_notification` | `collaboration_tools.py` | Teams | Send Adaptive Card via webhook |

### 5.4 Tool Schema Format (OpenAI Function Calling)

```python
# app/tools/schemas.py

LOOKUP_INCIDENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_incident",
        "description": "Look up a ServiceNow incident by number or sys_id",
        "parameters": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "Incident number (e.g., INC0012345) or sys_id"
                }
            },
            "required": ["incident_id"]
        }
    }
}

HYBRID_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "hybrid_search",
        "description": "Search knowledge base using keyword + vector hybrid search",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}
```

### 5.5 Tool Dispatch Flow

```
LLM Response (with tool_calls)
    │
    ▼
ToolRegistry.execute(name, arguments)
    │
    ├── name="lookup_incident" → itsm_tools.lookup_incident(incident_id)
    │                              → ServiceNowConnector.get_incident(id)
    │                              → Returns IncidentRecord dict
    │
    ├── name="hybrid_search" → search_tools.hybrid_search(query, top_k)
    │                           → AzureSearchConnector.search(query, embed(query))
    │                           → Returns list[SearchResult]
    │
    └── name="send_teams_notification" → collaboration_tools.send_notification(...)
                                          → TeamsConnector.send_card(payload)
                                          → Returns confirmation
```

---

## 6. Service 5: Connector Layer

### 6.1 Overview

**Module:** `app/connectors/`  
**Responsibility:** Typed clients for all external services with `_live` flag and graceful fallback

### 6.2 ConnectorBase

**File:** `app/connectors/base.py`

```python
class ConnectorHealth(BaseModel):
    connected: bool
    source: str       # "live" | "fallback"
    latency_ms: int | None = None
    error: str | None = None

class ConnectorBase(ABC):
    def __init__(self, settings):
        self._live: bool = False
        self._settings = settings
        self.logger = logging.getLogger(f"connectors.{self.__class__.__name__}")

    @abstractmethod
    async def health_check(self) -> ConnectorHealth: ...

    def _require_live(self, operation: str) -> bool:
        if not self._live:
            self.logger.warning("Connector offline — using fallback",
                                extra={"operation": operation})
        return self._live
```

### 6.3 Connector Inventory

| Connector | File | External Service | POC Mode | Live Mode |
|-----------|------|------------------|----------|-----------|
| **ServiceNowConnector** | `servicenow.py` | ServiceNow REST API | In-memory ITSM records | httpx → SNOW instance |
| **AzureOpenAIConnector** | `azure_openai.py` | Azure OpenAI | Hardcoded responses | openai SDK |
| **AzureSearchConnector** | `azure_search.py` | Azure AI Search | In-memory KB search | azure-search-documents SDK |
| **TeamsConnector** | `teams.py` | MS Teams Webhook | Audit log only | httpx → Adaptive Card |
| **TelemetryConnector** | *(inline)* | Application Insights | In-memory mock signals | OpenTelemetry SDK |

### 6.4 ServiceNow Connector

**File:** `app/connectors/servicenow.py`

```python
class ServiceNowConnector(ConnectorBase):
    """ITSM connector for ServiceNow REST API.

    Tables: incident, kb_knowledge, problem, change_request
    Auth: Basic Auth (service account)
    """

    async def get_incident(self, incident_id: str) -> dict | None:
        if not self._require_live("get_incident"):
            return self._fallback_incidents.get(incident_id)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/now/table/incident",
                params={"sysparm_query": f"number={incident_id}",
                        "sysparm_fields": "number,short_description,state,priority,..."},
                auth=(self._username, self._password),
            )
            resp.raise_for_status()
            results = resp.json().get("result", [])
            return results[0] if results else None

    async def create_incident(self, data: dict) -> dict:
        if not self._require_live("create_incident"):
            return self._create_fallback(data)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/now/table/incident",
                json=data,
                auth=(self._username, self._password),
            )
            resp.raise_for_status()
            return resp.json()["result"]

    async def health_check(self) -> ConnectorHealth:
        if not self._base_url:
            return ConnectorHealth(connected=False, source="fallback", error="Not configured")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/api/now/table/incident?sysparm_limit=1",
                                        auth=(self._username, self._password), timeout=5)
                resp.raise_for_status()
                return ConnectorHealth(connected=True, source="live")
        except Exception as e:
            return ConnectorHealth(connected=False, source="fallback", error=str(e))
```

### 6.5 Azure OpenAI Connector

**File:** `app/connectors/azure_openai.py`

```python
class AzureOpenAIConnector(ConnectorBase):
    """Azure OpenAI connector for chat completions and embeddings.

    Chat model: gpt-5.3-chat (temp 0.2 for agent reasoning, 0.7 for conversational)
    Embedding model: text-embedding-3-large (3072 dimensions)
    """

    async def chat_completion(self, messages, tools=None, temperature=0.2):
        if not self._require_live("chat_completion"):
            return self._fallback_chat(messages)
        return await self._client.chat.completions.create(
            model=self._settings.azure_openai_chat_deployment,
            messages=messages, tools=tools, temperature=temperature,
        )

    async def embed(self, text: str) -> list[float]:
        if not self._require_live("embed"):
            return [0.0] * 3072
        response = await self._client.embeddings.create(
            input=text, model=self._settings.azure_openai_embedding_deployment,
        )
        return response.data[0].embedding
```

### 6.6 Azure AI Search Connector

**File:** `app/connectors/azure_search.py`

```python
class AzureSearchConnector(ConnectorBase):
    """Hybrid search (BM25 keyword + vector cosine) with semantic ranker.

    Index: ai-ops-knowledge-index
    Returns top-5 results with @search.score as citation confidence.
    """

    async def search(self, query: str, vector: list[float], top_k: int = 5) -> list[dict]:
        if not self._require_live("search"):
            return self._fallback_search(query)
        results = self._client.search(
            search_text=query,
            vectors=[{"value": vector, "fields": "contentVector", "k": top_k}],
            select=["id", "title", "content", "source"],
            top=top_k,
            query_type="semantic",
            semantic_configuration_name="default",
        )
        return [{"title": r["title"], "content": r["content"],
                 "source": r["source"], "score": r["@search.score"]}
                for r in results]
```

### 6.7 Teams Connector

**File:** `app/connectors/teams.py`

```python
class TeamsConnector(ConnectorBase):
    """Adaptive Card v1.4 via Incoming Webhook.

    Fallback: logs event to Domain Store audit log.
    """

    async def send_card(self, title: str, body: str, action_url: str | None = None) -> bool:
        if not self._require_live("send_card"):
            self.logger.info("Teams notification (fallback)", extra={"title": title})
            return False
        card_payload = self._build_adaptive_card(title, body, action_url)
        async with httpx.AsyncClient() as client:
            resp = await client.post(self._webhook_url, json=card_payload)
            resp.raise_for_status()
            return True
```

### 6.8 ConnectorBundle

**File:** `app/connectors/__init__.py`

```python
@dataclass
class ConnectorBundle:
    """All connectors bundled for injection into services."""
    servicenow: ServiceNowConnector
    azure_openai: AzureOpenAIConnector
    azure_search: AzureSearchConnector
    teams: TeamsConnector

def build_connectors(settings: Settings, store: DomainStoreInterface) -> ConnectorBundle:
    return ConnectorBundle(
        servicenow=ServiceNowConnector(settings),
        azure_openai=AzureOpenAIConnector(settings),
        azure_search=AzureSearchConnector(settings),
        teams=TeamsConnector(settings),
    )
```

---

## 7. Service 6: Store Layer

### 7.1 Overview

**Module:** `app/store/`  
**Responsibility:** Tier 3 domain state persistence — CRUD for ITSM records, agent outputs, approvals, audit log

### 7.2 DomainStoreInterface

**File:** `app/store/base.py`

```python
class DomainStoreInterface(ABC):
    """Abstract interface for application state persistence.

    Implementations:
    - InMemoryStore: POC — dict-based, seeded with demo data
    - CosmosStore: Production — Azure Cosmos DB (MongoDB API)
    - TableStore: Alternative — Azure Table Storage
    """

    # --- Threads ---
    @abstractmethod
    async def add_thread(self, thread: OperationalThread) -> None: ...
    @abstractmethod
    async def get_thread(self, thread_id: str) -> OperationalThread | None: ...
    @abstractmethod
    async def list_threads(self, user_id: str | None = None) -> list[OperationalThread]: ...

    # --- Domain Records ---
    @abstractmethod
    async def upsert_incident(self, record: IncidentRecord) -> None: ...
    @abstractmethod
    async def get_incident(self, incident_id: str) -> IncidentRecord | None: ...
    @abstractmethod
    async def list_incidents(self, filters: dict | None = None) -> list[IncidentRecord]: ...

    # --- Agent Outputs ---
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

    # --- Settings & Aggregation ---
    @abstractmethod
    async def get_settings(self) -> RuntimeSettings: ...
    @abstractmethod
    async def save_settings(self, settings: RuntimeSettings) -> None: ...
    @abstractmethod
    async def snapshot(self) -> DashboardSnapshot: ...
```

### 7.3 Implementation Matrix

| Phase | Class | Persistence | Use Case |
|-------|-------|-------------|----------|
| **POC** | `InMemoryStore` | None (seeded on startup) | Local development, demos |
| **UAT** | `CosmosStore` | Azure Cosmos DB (MongoDB API) | Shared test environment |
| **Production** | `CosmosStore` | Azure Cosmos DB (MongoDB API) | Full deployment |
| **Alternative** | `TableStore` | Azure Table Storage | Cost-optimized (simpler queries) |

### 7.4 InMemoryStore

**File:** `app/store/memory.py`

```python
class InMemoryStore(DomainStoreInterface):
    """POC implementation — dict-backed, seeded with demo data on startup."""

    def __init__(self):
        self._threads: dict[str, OperationalThread] = {}
        self._incidents: dict[str, IncidentRecord] = {}
        self._outputs: list[AgentOutput] = []
        self._approvals: dict[str, ApprovalTask] = {}
        self._audit: list[AuditEvent] = []
        self._settings: RuntimeSettings = RuntimeSettings()

    async def seed(self) -> None:
        """Populate with realistic demo data for local development."""
        ...
```

### 7.5 CosmosStore

**File:** `app/store/cosmos.py`

```python
class CosmosStore(DomainStoreInterface):
    """Production implementation — Azure Cosmos DB with MongoDB API.

    Uses Motor async MongoDB driver, aligned with a Cosmos-style collection abstraction.
    Collections: threads, incidents, problems, changes, knowledge_articles,
                 agent_outputs, approvals, audit_log, settings
    """

    def __init__(self, connection_string: str, database_name: str):
        self._client: AsyncIOMotorClient | None = None
        self._connection_string = connection_string
        self._database_name = database_name

    async def initialize(self) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(self._connection_string)
        self._db = self._client[self._database_name]
        await self._ensure_indexes()
```

### 7.6 Store Factory

**File:** `app/store/factory.py`

```python
async def create_domain_store(settings: Settings) -> DomainStoreInterface:
    if settings.storage_backend == "cosmos":
        store = CosmosStore(settings.cosmos_connection_string, settings.cosmos_database)
        await store.initialize()
        return store
    if settings.storage_backend == "azure_table":
        store = TableStore(settings.azure_table_connection_string)
        await store.initialize()
        return store
    store = InMemoryStore()
    await store.seed()
    return store
```

---

## 8. Service 7: Memory Layer

### 8.1 Overview

**Module:** `app/memory/`  
**Responsibility:** Tier 1 conversation checkpointing (checkpointer factory) and Tier 3b long-term memory interface

### 8.2 Checkpointer Factory

**File:** `app/memory/checkpointer.py`

```python
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

_GLOBAL_CHECKPOINTER: BaseCheckpointSaver = MemorySaver()

async def get_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    """Resolve checkpointer using priority cascade.

    Priority:
    1. Redis (if REDIS_URL is configured)
    2. MemorySaver fallback (in-process, zero dependencies)
    """
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

### 8.3 Long-Term Memory (Interface Only)

**File:** `app/memory/long_term.py`

```python
from langgraph.store.base import BaseStore

class LongTermMemoryStore(BaseStore):
    """Cross-session knowledge store interface.

    Not instantiated in POC — defined for architectural completeness.
    Production: Azure Cosmos DB (MongoDB API) with TTL-based expiration.

    Enables:
    - User preference learning (resolution style, notification preferences)
    - Resolution pattern caching (embedding-indexed past resolutions)
    - KB quality scoring (track which articles lead to successful resolutions)
    - Agent tuning (per-agent performance baselines, adaptive critic thresholds)
    """

    async def aget(self, key, namespace=None): raise NotImplementedError
    async def aput(self, key, value, namespace=None): raise NotImplementedError
    async def adelete(self, key, namespace=None): raise NotImplementedError
    async def abatch(self, ops): raise NotImplementedError
    async def batch(self, ops): raise NotImplementedError
```

---

## 9. Middleware

### 9.1 Authentication (Entra ID JWT)

**File:** `app/middleware/auth.py`

```python
class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    roles: list[str] = Field(default_factory=list)

async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency — validates Entra ID JWT and extracts user info.

    Bypass: Set AUTH_DISABLED=true for local development.
    """
    if request.app.state.settings.auth_disabled:
        return CurrentUser(user_id="dev", email="dev@local", name="Developer")

    token = extract_bearer_token(request)
    claims = await validate_jwt(token, request.app.state.settings)
    return CurrentUser(
        user_id=claims["oid"],
        email=claims.get("preferred_username", ""),
        name=claims.get("name", ""),
        roles=claims.get("roles", []),
    )
```

**JWT Validation:**
- JWKS endpoint: `https://login.microsoftonline.com/{ENTRA_TENANT_ID}/discovery/v2.0/keys`
- Required claims: `aud` == `ENTRA_CLIENT_ID`, `iss` contains `ENTRA_TENANT_ID`, `exp` not expired
- Library: `python-jose[cryptography]`

### 9.2 Request Logging

**File:** `app/middleware/logging.py`

```python
class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request/response as structured JSON.

    Fields: method, path, status_code, duration_ms, user_id, trace_id
    """
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        logger.info("request", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration, 2),
        })
        return response
```

---

## 10. API Routes

### 10.1 Route Summary

| Route | Method | Handler | Auth | Description |
|-------|--------|---------|------|-------------|
| `/api/chat` | POST | `chat.py` | Yes | Process user message |
| `/api/dashboard` | GET | `dashboard.py` | Yes | Dashboard snapshot |
| `/api/incidents` | GET | `incidents.py` | Yes | List incidents |
| `/api/incidents/{id}` | GET | `incidents.py` | Yes | Get incident detail |
| `/api/approvals/{id}/decision` | POST | `approvals.py` | Yes | Submit approval decision |
| `/api/settings` | GET/PUT | `settings.py` | Yes | Runtime settings |
| `/v1/threads` | POST | `threads.py` | Yes | Create conversation thread |
| `/v1/threads/{id}` | GET | `threads.py` | Yes | Get thread detail |
| `/v1/threads/{id}/runs/wait` | POST | `threads.py` | Yes | Execute/resume graph run |
| `/v1/threads/{id}/state` | GET | `threads.py` | Yes | Inspect graph state |
| `/v1/threads/{id}/history` | GET | `threads.py` | Yes | Checkpoint history |
| `/v1/assistants` | GET | `assistants.py` | Yes | List agent assistants |
| `/healthz` | GET | `health.py` | No | Health check |

### 10.2 Chat Endpoint

```python
# app/routes/chat.py

@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    chat_service = ChatService(orchestrator, store)
    return await chat_service.handle(body.message, body.thread_id, user)
```

**Request:**
```json
{
  "message": "What's happening with INC0012345?",
  "thread_id": "thr_abc123"
}
```

**Response:**
```json
{
  "thread_id": "thr_abc123",
  "message": "I found incident INC0012345. It's a P2 incident...",
  "agent_outputs": [
    {
      "agent_id": "incident_agent",
      "target_type": "incident",
      "target_id": "INC0012345",
      "title": "Incident Triage — INC0012345",
      "summary": "P2 network outage affecting EMEA region...",
      "confidence": 0.85,
      "requires_approval": false
    }
  ],
  "pending_approvals": [],
  "timestamp": "2026-04-28T14:23:45Z"
}
```

### 10.3 Thread State Inspection

```python
# app/routes/threads.py

@router.get("/v1/threads/{thread_id}/state")
async def get_thread_state(
    thread_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await orchestrator.get_thread_state(thread_id)
```

### 10.4 Approval Decision

```python
# app/routes/approvals.py

@router.post("/api/approvals/{task_id}/decision")
async def submit_decision(
    task_id: str,
    body: ApprovalDecision,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    # Update approval task in store
    await store.update_approval(task_id, body)
    await store.log_event("approval_decision", {
        "task_id": task_id, "decision": body.decision, "reviewer": user.email,
    })
    # Resume graph if approved
    if body.decision == "approved":
        thread_id = await get_thread_for_approval(store, task_id)
        result = await orchestrator.resume(thread_id, body.model_dump())
        return {"status": "resumed", "result": result}
    return {"status": "rejected"}
```

### 10.5 Health Check

```python
# app/routes/health.py

@router.get("/healthz")
async def health(request: Request) -> dict:
    connectors = request.app.state.connectors
    return {
        "status": "healthy",
        "version": "1.0.0",
        "connectors": {
            "servicenow": (await connectors.servicenow.health_check()).model_dump(),
            "azure_openai": (await connectors.azure_openai.health_check()).model_dump(),
            "azure_search": (await connectors.azure_search.health_check()).model_dump(),
            "teams": (await connectors.teams.health_check()).model_dump(),
        },
    }
```

---

## 11. Cross-Cutting Concerns

### 11.1 ID Conventions

| Prefix | Entity | Example |
|--------|--------|---------|
| `thr_` | Thread | `thr_a1b2c3d4` |
| `msg_` | Message | `msg_e5f6g7h8` |
| `run_` | Run | `run_i9j0k1l2` |
| `out_` | Agent Output | `out_m3n4o5p6` |
| `apr_` | Approval Task | `apr_q7r8s9t0` |
| `chg_` | Change Record | `chg_u1v2w3x4` |

### 11.2 Logging

All modules use `logging.getLogger(__name__)`. No `print()` statements.

```python
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)
```

### 11.3 Type Hints

All function signatures must be fully typed. `Any` only where genuinely unavoidable.

### 11.4 File Headers

Every `.py` file begins with:
```python
from __future__ import annotations
```

### 11.5 Testing

- Framework: `pytest` + `pytest-asyncio`
- Test client: `fastapi.testclient.TestClient`
- One test file per feature area under `tests/`
- Key test files: `test_chat.py`, `test_orchestrator.py`, `test_checkpointer.py`, `test_connectors.py`, `test_approval.py`, `test_routes.py`

---

## 12. Appendices

### 12.1 Pydantic Model Reference

| Model | Module | Purpose |
|-------|--------|---------|
| `RunContext` | `app/models/agent.py` | LangGraph state schema (Tier 2 working memory) |
| `AgentOutput` | `app/models/agent.py` | Structured output from agent reasoning |
| `ToolCallResult` | `app/models/agent.py` | Tool execution result with timing |
| `IncidentRecord` | `app/models/domain.py` | ServiceNow incident representation |
| `ProblemRecord` | `app/models/domain.py` | ServiceNow problem representation |
| `ChangeRecord` | `app/models/domain.py` | ServiceNow change request |
| `KnowledgeArticle` | `app/models/domain.py` | Knowledge base article |
| `OperationalThread` | `app/models/chat.py` | Conversation thread metadata |
| `MessageRecord` | `app/models/chat.py` | Individual message in a thread |
| `ChatRequest` | `app/models/chat.py` | Incoming chat request body |
| `ChatResponse` | `app/models/chat.py` | Outgoing chat response |
| `ApprovalTask` | `app/models/approval.py` | HITL approval lifecycle object |
| `ApprovalDecision` | `app/models/approval.py` | Human approval/rejection |
| `DashboardSnapshot` | `app/models/dashboard.py` | Cached dashboard aggregation |
| `CurrentUser` | `app/models/auth.py` | Authenticated user identity |
| `Settings` | `app/config.py` | Application configuration (pydantic-settings) |
| `ConnectorHealth` | `app/connectors/base.py` | Health check result |

### 12.2 Configuration Reference

```python
class Settings(BaseSettings):
    # ServiceNow
    snow_instance_url: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = "gpt-4.1"
    azure_openai_embedding_deployment: str = "ka-embedding-model"
    azure_openai_api_version: str = "2025-01-01-preview"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "ka-vector"

    # Entra ID
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    auth_disabled: bool = False

    # Teams
    teams_webhook_url: str = ""

    # Memory Tier 1
    redis_url: str = ""  # rediss://:password@host:6380/0

    # Memory Tier 3
    storage_backend: str = "memory"  # "memory" | "cosmos" | "azure_table"
    cosmos_connection_string: str = ""
    cosmos_database: str = "ai-ops-agent"
    azure_table_connection_string: str = ""

    # Application
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "case_sensitive": False}
```

### 12.3 Related Documents

| Document | Location | Content |
|----------|----------|---------|
| **Backend Architecture** | [BACKEND-ARCHITECTURE.md](BACKEND-ARCHITECTURE.md) | TSD Part 1 — overview and architecture |
| **Frontend Architecture** | [frontend/docs/architecture/FRONTEND-ARCHITECTURE.md](../../../frontend/docs/architecture/FRONTEND-ARCHITECTURE.md) | Frontend overview |
| **Frontend Components** | [frontend/docs/architecture/COMPONENT-REFERENCE.md](../../../frontend/docs/architecture/COMPONENT-REFERENCE.md) | Component specifications |

---

**END OF TSD PART 2 — BACKEND SERVICES SPECIFICATION**
