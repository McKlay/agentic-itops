# AI Operations Concierge — Technical Reference

> **Companion to:** [ARCHITECTURE.md](ARCHITECTURE.md)  
> **Last updated:** 2026-04-28

> **⚠️ DEPRECATED:** This document is retained for historical reference only. The authoritative technical specifications have moved to:
> - **[Backend Services (TSD Part 2)](../backend/docs/architecture/BACKEND-SERVICES.md)** — Detailed per-module service specifications
> - **[Backend Architecture (TSD Part 1)](../backend/docs/architecture/BACKEND-ARCHITECTURE.md)** — Architecture overview with memory tiers, infrastructure, and decision log

This document provides module-level specifications, API contracts, Pydantic model definitions, tool schemas, Terraform IaC, and environment variable reference.

---

## 1. Backend Module Specifications

### 1.1 Configuration — `app/config.py`

Typed configuration via `pydantic-settings`. All secrets loaded from environment variables (never from code or config files).

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ServiceNow
    snow_instance_url: str = ""
    snow_svc_username: str = ""
    snow_svc_password: str = ""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = "gpt-5.3-chat"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2025-01-01"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index: str = "ai-ops-knowledge-index"

    # Entra ID
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    auth_disabled: bool = False      # Dev only — never True in production

    # Teams
    teams_webhook_url: str = ""

    # Storage
    storage_backend: str = "memory"  # "memory" | "azure_table"
    azure_table_connection_string: str = ""

    # Application
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "case_sensitive": False}
```

### 1.2 Application Entry — `app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    store = create_store(settings)
    connectors = build_connectors(settings, store)
    orchestrator = Orchestrator(settings, connectors, store)

    app.state.settings = settings
    app.state.store = store
    app.state.connectors = connectors
    app.state.orchestrator = orchestrator
    yield

app = FastAPI(title="AI Operations Concierge", version="1.0.0", lifespan=lifespan)
```

Key conventions:
- `@asynccontextmanager` lifespan — no `@app.on_event`
- All shared state on `app.state` — never imported globals in routes
- Route handlers access state via `request.app.state`
- Every module uses `logger = logging.getLogger(__name__)`

### 1.3 Logging — `app/middleware/logging.py`

Structured JSON logging across all modules:

```python
import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {}),
        })
```

Request/response logging middleware captures method, path, status code, and latency for every API call. Sensitive fields (Authorization header, passwords) are never logged.

### 1.4 Models — `app/models/`

All models inherit from `pydantic.BaseModel`. Mutable defaults use `Field(default_factory=...)`.

#### `domain.py` — Core domain records

| Model | Key Fields | Notes |
|---|---|---|
| `IncidentRecord` | id, title, service, domain, severity (1-4), status, summary, assignee, timestamps | ID prefix: `INC` |
| `ProblemRecord` | id, title, service, linked_incidents, corrective_actions | ID prefix: `PRB` |
| `ChangeRecord` | id, title, service, rationale, implementation_plan, approvals | ID prefix: `CHG` |
| `KnowledgeArticle` | id, title, source, summary, services, tags, validated | ID prefix: `KB` |
| `TelemetrySignal` | id, service, category (`metric`/`log`/`alert`), severity | Evidence for agents |

#### `agent.py` — Agent orchestration models

```python
class RunContext(BaseModel):
    """Shared context object passed between agents in a pipeline."""
    thread_id: str
    user: CurrentUser
    intent: str = ""
    target_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    tool_results: list[ToolCallResult] = Field(default_factory=list)
    retry_count: int = 0
    critic_score: float | None = None
    critic_feedback: str = ""

class AgentOutput(BaseModel):
    id: str = Field(default_factory=lambda: new_id("out"))
    agent_id: str
    target_type: Literal["incident", "problem", "change", "platform"]
    target_id: str
    title: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_approval: bool = True
    draft_payload: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=utcnow)

class ToolCallResult(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    duration_ms: int
```

#### `chat.py` — Conversation models

```python
class OperationalThread(BaseModel):
    id: str = Field(default_factory=lambda: new_id("thr"))
    initiated_by: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

class MessageRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    thread_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

#### `approval.py` — Approval workflow models

```python
class ApprovalTask(BaseModel):
    id: str = Field(default_factory=lambda: new_id("apr"))
    output_id: str
    assigned_role: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    decided_by: str = ""
    decided_at: datetime | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)

class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    decided_by: str
    notes: str = ""
```

### 1.5 Agents — `app/agents/`

#### `base.py` — BaseAgent with LLM reasoning loop

```python
class BaseAgent(ABC):
    """Abstract agent with ReAct reasoning loop."""

    def __init__(self, agent_id: str, llm: AzureOpenAIConnector, tools: list[Tool]):
        self.agent_id = agent_id
        self.llm = llm
        self.tools = tools
        self.logger = logging.getLogger(f"agents.{agent_id}")

    async def run(self, context: RunContext) -> AgentOutput:
        """Execute ReAct loop: reason → tool_call → observe → repeat."""
        messages = self._build_messages(context)
        tool_schemas = [t.schema for t in self.tools]

        for step in range(self.max_steps):
            response = await self.llm.chat_completion(
                messages=messages,
                tools=tool_schemas,
                temperature=0.2,
            )
            if response.tool_calls:
                for call in response.tool_calls:
                    result = await self._execute_tool(call)
                    context.tool_results.append(result)
                    messages.append({"role": "tool", "content": json.dumps(result.result)})
            else:
                return self._parse_output(response, context)

        return self._fallback_output(context)

    @abstractmethod
    def _build_messages(self, context: RunContext) -> list[dict]: ...

    @abstractmethod
    def _parse_output(self, response, context: RunContext) -> AgentOutput: ...
```

#### `supervisor.py` — Intent classification and agent routing

The supervisor is an LLM-powered router, not a hardcoded dispatcher:

```python
SUPERVISOR_SYSTEM_PROMPT = """You are the orchestration supervisor for an IT Operations platform.
Classify the user's intent and select the appropriate agent(s).
Return JSON: {"intent": "...", "agents": ["..."], "requires_approval": bool}
Valid agents: incident_agent, knowledge_agent, problem_agent, postmortem_agent, governance_agent
"""
```

#### `critic.py` — Quality gate

```python
CRITIC_SYSTEM_PROMPT = """Evaluate this agent output for quality.
Score 0.0-1.0 on: completeness, evidence grounding, actionability.
Return JSON: {"score": float, "feedback": "...", "pass": bool}
"""

class CriticAgent:
    async def evaluate(self, output: AgentOutput, context: RunContext) -> CriticResult:
        # LLM scores the output; below threshold triggers retry
        ...
```

### 1.6 Tools — `app/tools/`

Tools are OpenAI function-call schemas that wrap connector methods. The LLM selects which tools to invoke.

#### `schemas.py` — Tool definitions

```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_incident",
            "description": "Retrieve an incident record by ID from ServiceNow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID (e.g. INC001245)"}
                },
                "required": ["incident_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search enterprise knowledge base using hybrid search (keyword + vector).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_knowledge_article",
            "description": "Draft a new knowledge article in ServiceNow (requires human approval).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "linked_incident_id": {"type": "string"},
                },
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_telemetry_signals",
            "description": "Retrieve recent telemetry signals (metrics, logs, alerts) for a service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "category": {"type": "string", "enum": ["metric", "log", "alert"]},
                },
                "required": ["service"],
            },
        },
    },
]
```

#### `registry.py` — Tool dispatch

```python
class ToolRegistry:
    def __init__(self, connectors: ConnectorBundle):
        self._handlers: dict[str, Callable] = {
            "lookup_incident": connectors.itsm.get_incident,
            "search_knowledge": connectors.search.hybrid_search,
            "create_knowledge_article": connectors.itsm.create_knowledge_article,
            "get_telemetry_signals": connectors.telemetry.get_signals,
            # ... additional tools
        }

    async def execute(self, name: str, arguments: dict) -> Any:
        handler = self._handlers[name]
        return await handler(**arguments)
```

### 1.7 Connectors — `app/connectors/`

#### `base.py` — Connector contract

```python
class ConnectorBase(ABC):
    """Base class for external service connectors with graceful degradation."""

    def __init__(self, settings: Settings):
        self._live: bool = False
        self.logger = logging.getLogger(f"connectors.{self.__class__.__name__}")

    @abstractmethod
    async def health_check(self) -> ConnectorHealth: ...

    def _require_live(self, operation: str) -> None:
        if not self._live:
            self.logger.warning("Connector offline, using fallback", extra={"operation": operation})

class ConnectorHealth(BaseModel):
    connected: bool
    source: str       # "live" | "fallback"
    latency_ms: int | None = None
    error: str | None = None
```

#### `azure_openai.py` — LLM connector

```python
class AzureOpenAIConnector(ConnectorBase):
    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.2,
    ) -> ChatCompletion:
        """Call Azure OpenAI chat completions with optional function calling."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector using text-embedding-3-large."""
        ...
```

#### `azure_search.py` — Knowledge connector

```python
class AzureSearchConnector(ConnectorBase):
    async def hybrid_search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Hybrid search: BM25 keyword + vector cosine similarity."""
        vector = await self._llm.embed(query)
        # Uses azure.search.documents.SearchClient
        results = self._client.search(
            search_text=query,
            vectors=[{"value": vector, "fields": "embedding", "k_nearest_neighbors": top_k}],
            top=top_k,
        )
        ...
```

#### `servicenow.py` — ITSM connector

```python
class ServiceNowConnector(ConnectorBase):
    """ServiceNow REST API client with in-memory fallback."""

    async def get_incident(self, incident_id: str) -> IncidentRecord: ...
    async def list_incidents(self, filters: dict | None = None) -> list[IncidentRecord]: ...
    async def create_incident(self, data: dict) -> IncidentRecord: ...
    async def update_incident(self, incident_id: str, fields: dict) -> IncidentRecord: ...
    async def create_knowledge_article(self, data: dict) -> KnowledgeArticle: ...
    async def list_problems(self) -> list[ProblemRecord]: ...
    async def list_changes(self) -> list[ChangeRecord]: ...

    # URL generators for deep-links
    def incident_url(self, sys_id: str) -> str: ...
    def ka_url(self, sys_id: str) -> str: ...
```

### 1.8 Services — `app/services/`

#### `orchestrator.py` — LangGraph graph builder

```python
from langgraph.graph import StateGraph, END

class Orchestrator:
    def __init__(self, settings, connectors, store):
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        graph = StateGraph(RunContext)
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("incident_agent", self._incident_node)
        graph.add_node("knowledge_agent", self._knowledge_node)
        graph.add_node("problem_agent", self._problem_node)
        graph.add_node("postmortem_agent", self._postmortem_node)
        graph.add_node("governance_agent", self._governance_node)
        graph.add_node("critic", self._critic_node)
        graph.add_node("response_formatter", self._format_node)
        graph.add_node("hitl_gate", self._hitl_node)

        graph.set_entry_point("supervisor")
        graph.add_conditional_edges("supervisor", self._route_to_agent)
        # All executor agents → critic
        for agent in ["incident_agent", "knowledge_agent", "problem_agent",
                       "postmortem_agent", "governance_agent"]:
            graph.add_edge(agent, "critic")
        graph.add_conditional_edges("critic", self._route_critic)
        graph.add_edge("response_formatter", END)
        graph.add_edge("hitl_gate", "response_formatter")

        return graph.compile()

    def _route_critic(self, context: RunContext) -> str:
        if context.critic_score and context.critic_score >= 0.7:
            if any(o.requires_approval for o in context.agent_outputs):
                return "hitl_gate"
            return "response_formatter"
        if context.retry_count < 2:
            return "supervisor"  # retry
        return "hitl_gate"  # escalate
```

#### `chat.py` — Conversational RAG handler

```python
class ChatService:
    async def handle(self, message: str, thread_id: str, user: CurrentUser) -> ChatResponse:
        # 1. Store user message
        self.store.add_message(MessageRecord(thread_id=thread_id, role="user", content=message))

        # 2. Build RunContext
        context = RunContext(thread_id=thread_id, user=user)

        # 3. Execute orchestrator graph
        result = await self.orchestrator.run(context)

        # 4. Store assistant response
        self.store.add_message(MessageRecord(
            thread_id=thread_id, role="assistant", content=result.message,
        ))

        return result
```

### 1.9 Memory — `app/memory/`

> **Full specification:** [Backend Architecture](../backend/docs/architecture/BACKEND-ARCHITECTURE.md) §3

The backend uses a **3-tier memory architecture** aligned with reusable agent-framework patterns:

| Tier | Purpose | POC | Production |
|---|---|---|---|
| **Tier 1** Conversation Memory | LangGraph graph state, multi-turn context, HITL interrupts | `MemorySaver` (in-process) | `AsyncRedisSaver` (Azure Cache for Redis) |
| **Tier 2** Working Memory | Per-request `RunContext` flowing through graph nodes | Pydantic model (transient) | Same |
| **Tier 3** Domain Store | Incidents, problems, approvals, audit log, settings | `InMemoryStore` (seeded) | `CosmosStore` (Azure Cosmos DB MongoDB API) |

#### Checkpointer factory — `app/memory/checkpointer.py`

```python
async def get_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    """Priority cascade: Redis → MemorySaver (aligned with the target framework flow-controller pattern)."""
    if settings.redis_url:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        saver = AsyncRedisSaver.from_conn_string(settings.redis_url)
        await saver.setup()
        return saver
    return _GLOBAL_CHECKPOINTER  # module-level MemorySaver singleton
```

### 1.10 Store — `app/store/`

#### `base.py` — Abstract domain store interface

```python
class DomainStoreInterface(ABC):
    @abstractmethod
    async def add_thread(self, thread: OperationalThread) -> None: ...
    @abstractmethod
    async def get_thread(self, thread_id: str) -> OperationalThread | None: ...
    @abstractmethod
    async def upsert_incident(self, record: IncidentRecord) -> None: ...
    @abstractmethod
    async def get_incident(self, incident_id: str) -> IncidentRecord | None: ...
    @abstractmethod
    async def add_approval(self, task: ApprovalTask) -> None: ...
    @abstractmethod
    async def update_approval(self, task_id: str, decision: ApprovalDecision) -> None: ...
    @abstractmethod
    async def log_event(self, kind: str, payload: dict) -> None: ...
    @abstractmethod
    async def snapshot(self) -> DashboardSnapshot: ...
```

#### Factory

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
    await store.seed()  # Demo data for POC
    return store
```

---

## 2. API Contracts

### 2.1 Chat

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/chat` | POST | Required | Send chat message, receive agent response |

**Request:**
```json
{
  "message": "What's the status of INC001245?",
  "thread_id": "thr_abc123",
  "role": "Support"
}
```

**Response:**
```json
{
  "kind": "incident",
  "message": "INC001245 is currently open for SAP Login Service...",
  "artifacts": [
    {
      "type": "incident_card",
      "data": { "id": "INC001245", "title": "...", "status": "open" }
    }
  ],
  "agent_outputs": [],
  "approval_tasks": []
}
```

### 2.2 Threads & Messages

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/v1/threads` | POST | Required | Create new conversation thread |
| `/v1/threads/{id}` | GET | Required | Get thread metadata |
| `/v1/threads/{id}/messages` | GET | Required | List messages in thread |
| `/v1/threads/{id}/messages` | POST | Required | Append message to thread |

### 2.3 Dashboard

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/dashboard` | GET | Required | Full dashboard snapshot |
| `/api/incidents/overview` | GET | Required | Paginated incidents with filters |

### 2.4 Approvals

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/approvals/{id}/decision` | POST | Required | Submit approval decision |

**Request:**
```json
{
  "decision": "approved",
  "decided_by": "user@company.com",
  "notes": "Reviewed and approved"
}
```

### 2.5 Settings

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/settings` | GET | Required | Load runtime settings |
| `/api/settings` | PUT | Required | Save runtime settings |
| `/api/settings/test-connector/{name}` | POST | Required | Test connector health |

### 2.6 Health

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/healthz` | GET | None | Health check (public) |

---

## 3. Frontend Component Mapping

Components derived from the KnowledgeForge2 command center UI, rebuilt in React + Tailwind CSS.

### Layout Components

| Component | Tailwind Layout | Purpose |
|---|---|---|
| `AppShell` | `grid grid-cols-[260px_1fr_320px] h-screen` | 3-panel grid shell |
| `Sidebar` | `flex flex-col h-full bg-white border-r` | Nav, sessions, role/theme/profile |
| `ActivityFeed` | `flex flex-col h-full bg-gray-50 border-l` | Live agent feed + metric strip |

### Page Components

| Component | Route State | Data Source |
|---|---|---|
| `HomePage` | `home` | Static hero + quick-action cards |
| `ConversationPage` | `conversation` | `useThread` hook → `/api/chat` |
| `IncidentsPage` | `incidents` | `useDashboard` → `/api/incidents/overview` |
| `ProblemsPage` | `problems` | `useDashboard` → `/api/dashboard` |
| `ChangesPage` | `changes` | `useDashboard` → `/api/dashboard` |
| `ObservabilityPage` | `observability` | `useDashboard` → `/api/dashboard` |
| `PerformancePage` | `performance` | `useDashboard` → `/api/dashboard` |

### Chat Components

| Component | Purpose |
|---|---|
| `Conversation` | Message thread renderer (scrollable) |
| `Composer` | Input field + send + new session + clear |
| `MessageBubble` | User (right, blue) / Assistant (left, white + avatar) |
| `ArtifactCard` | Rich cards: RCA report, KB draft, incident detail |
| `ExperienceRating` | 5-level emoji rating per response |

### Shared Components

| Component | Purpose |
|---|---|
| `StatusPill` | Colored status badge (open/resolved/pending) |
| `MetricTile` | Numeric KPI tile with label |
| `FeedCard` | Activity feed entry (color-coded by type) |
| `BarChart` | CSS div-based bar chart |
| `DonutChart` | CSS conic-gradient donut chart |
| `SlaGauge` | Track/fill SLA progress bar |
| `FilterChip` | Cycle-through filter buttons |
| `SearchInput` | Debounced search (250ms) |
| `PaginationControls` | Previous/Next for paginated data |

### Zustand Stores

| Store | State Managed |
|---|---|
| `uiStore` | currentView, activeNav, theme, sidebarOpen |
| `chatStore` | sessions, activeSessionId, conversations, sessionSnapshots |
| `dashboardStore` | dashboard snapshot, incidents, problems, changes, loading states |
| `settingsStore` | runtime settings, connector states |

---

## 4. Terraform Infrastructure as Code

### 4.1 Provider Configuration — `infra/providers.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformaiops"
    container_name       = "tfstate"
    key                  = "ai-ops-agent.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}
```

### 4.2 Root Module — `infra/main.tf`

```hcl
module "resource_group" {
  source   = "./modules/resource-group"
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

module "keyvault" {
  source              = "./modules/keyvault"
  name                = "kv-ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.location
  tenant_id           = var.entra_tenant_id
  tags                = var.tags
}

module "monitoring" {
  source              = "./modules/monitoring"
  name_prefix         = "ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.location
  tags                = var.tags
}

module "openai" {
  source              = "./modules/openai"
  name                = "oai-ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.openai_location
  chat_model           = var.openai_chat_model
  embedding_model      = var.openai_embedding_model
  tags                = var.tags
}

module "search" {
  source              = "./modules/search"
  name                = "srch-ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.location
  sku                 = var.search_sku
  index_name          = var.search_index_name
  tags                = var.tags
}

module "app_service" {
  source                   = "./modules/app-service"
  name                     = "app-ai-ops-${var.environment}"
  resource_group_name      = module.resource_group.name
  location                 = var.location
  python_version           = "3.11"
  app_insights_conn_string = module.monitoring.connection_string
  keyvault_id              = module.keyvault.id
  tags                     = var.tags

  app_settings = {
    SNOW_INSTANCE_URL                = "@Microsoft.KeyVault(VaultName=${module.keyvault.name};SecretName=snow-instance-url)"
    SNOW_SVC_USERNAME                = "@Microsoft.KeyVault(VaultName=${module.keyvault.name};SecretName=snow-svc-username)"
    SNOW_SVC_PASSWORD                = "@Microsoft.KeyVault(VaultName=${module.keyvault.name};SecretName=snow-svc-password)"
    AZURE_OPENAI_ENDPOINT            = module.openai.endpoint
    AZURE_OPENAI_API_KEY             = "@Microsoft.KeyVault(VaultName=${module.keyvault.name};SecretName=openai-api-key)"
    AZURE_OPENAI_CHAT_DEPLOYMENT     = var.openai_chat_model
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = var.openai_embedding_model
    AZURE_OPENAI_API_VERSION         = var.openai_api_version
    AZURE_SEARCH_ENDPOINT            = module.search.endpoint
    AZURE_SEARCH_API_KEY             = "@Microsoft.KeyVault(VaultName=${module.keyvault.name};SecretName=search-api-key)"
    AZURE_SEARCH_INDEX               = var.search_index_name
    ENTRA_TENANT_ID                  = var.entra_tenant_id
    ENTRA_CLIENT_ID                  = var.entra_client_id
    TEAMS_WEBHOOK_URL                = "@Microsoft.KeyVault(VaultName=${module.keyvault.name};SecretName=teams-webhook-url)"
  }
}

module "static_web_app" {
  source              = "./modules/static-web-app"
  name                = "swa-ai-ops-${var.environment}"
  resource_group_name = module.resource_group.name
  location            = var.swa_location
  sku_tier            = "Standard"
  tags                = var.tags
}
```

### 4.3 Variables — `infra/variables.tf`

```hcl
variable "environment" {
  type    = string
  default = "dev"
}

variable "location" {
  type    = string
  default = "southeastasia"
}

variable "swa_location" {
  type        = string
  default     = "eastasia"
  description = "Static Web Apps has limited region support."
}

variable "openai_location" {
  type        = string
  default     = "eastus"
  description = "Azure OpenAI region — model availability varies by region."
}

variable "resource_group_name" {
  type    = string
  default = "rg-ai-ops-agent"
}

variable "entra_tenant_id" {
  type      = string
  sensitive = true
}

variable "entra_client_id" {
  type      = string
  sensitive = true
}

variable "openai_chat_model" {
  type    = string
  default = "gpt-5.3-chat"
}

variable "openai_embedding_model" {
  type    = string
  default = "text-embedding-3-large"
}

variable "openai_api_version" {
  type    = string
  default = "2025-01-01"
}

variable "search_sku" {
  type    = string
  default = "basic"
}

variable "search_index_name" {
  type    = string
  default = "ai-ops-knowledge-index"
}

variable "tags" {
  type = map(string)
  default = {
    project     = "ai-ops-concierge"
    environment = "dev"
    team        = "platform-engineering"
  }
}
```

### 4.4 Module — App Service (`infra/modules/app-service/main.tf`)

```hcl
resource "azurerm_service_plan" "this" {
  name                = "${var.name}-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "P1v3"
  tags                = var.tags
}

resource "azurerm_linux_web_app" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.this.id
  https_only          = true
  tags                = var.tags

  site_config {
    application_stack {
      python_version = var.python_version
    }
    app_command_line = "uvicorn app.main:app --host 0.0.0.0 --port 8000"
  }

  app_settings = merge(var.app_settings, {
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.app_insights_conn_string
    SCM_DO_BUILD_DURING_DEPLOYMENT        = "true"
  })

  identity {
    type = "SystemAssigned"
  }
}

# Grant Key Vault access to the App Service managed identity
resource "azurerm_key_vault_access_policy" "app_service" {
  key_vault_id = var.keyvault_id
  tenant_id    = azurerm_linux_web_app.this.identity[0].tenant_id
  object_id    = azurerm_linux_web_app.this.identity[0].principal_id

  secret_permissions = ["Get", "List"]
}
```

### 4.5 Module — Azure OpenAI (`infra/modules/openai/main.tf`)

```hcl
resource "azurerm_cognitive_account" "openai" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "OpenAI"
  sku_name            = "S0"
  tags                = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.chat_model
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.chat_model
    version = "latest"
  }

  sku {
    name     = "Standard"
    capacity = 30
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_model
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.embedding_model
    version = "latest"
  }

  sku {
    name     = "Standard"
    capacity = 30
  }
}

output "endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}
```

### 4.6 Module — Azure AI Search (`infra/modules/search/main.tf`)

```hcl
resource "azurerm_search_service" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  replica_count       = 1
  partition_count     = 1
  tags                = var.tags
}

output "endpoint" {
  value = "https://${azurerm_search_service.this.name}.search.windows.net"
}

output "primary_key" {
  value     = azurerm_search_service.this.primary_key
  sensitive = true
}
```

### 4.7 Module — Key Vault (`infra/modules/keyvault/main.tf`)

```hcl
resource "azurerm_key_vault" "this" {
  name                       = var.name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = var.tags
}

output "id" {
  value = azurerm_key_vault.this.id
}

output "name" {
  value = azurerm_key_vault.this.name
}
```

### 4.8 Module — Monitoring (`infra/modules/monitoring/main.tf`)

```hcl
resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.name_prefix}-law"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "${var.name_prefix}-ai"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
  tags                = var.tags
}

output "connection_string" {
  value     = azurerm_application_insights.this.connection_string
  sensitive = true
}

output "instrumentation_key" {
  value     = azurerm_application_insights.this.instrumentation_key
  sensitive = true
}
```

### 4.9 Module — Static Web App (`infra/modules/static-web-app/main.tf`)

```hcl
resource "azurerm_static_web_app" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = var.sku_tier
  sku_size            = var.sku_tier == "Standard" ? "Standard" : "Free"
  tags                = var.tags
}

output "default_host_name" {
  value = azurerm_static_web_app.this.default_host_name
}

output "api_key" {
  value     = azurerm_static_web_app.this.api_key
  sensitive = true
}
```

---

## 5. Environment Variables — Complete Reference

| Variable | Required | Phase | Used By |
|---|---|---|---|
| `SNOW_INSTANCE_URL` | Yes (live) | 1 | ServiceNowConnector |
| `SNOW_SVC_USERNAME` | Yes (live) | 1 | ServiceNowConnector |
| `SNOW_SVC_PASSWORD` | Yes (live) | 1 | ServiceNowConnector |
| `AZURE_OPENAI_ENDPOINT` | Yes | 1 | AzureOpenAIConnector |
| `AZURE_OPENAI_API_KEY` | Yes | 1 | AzureOpenAIConnector |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Yes | 1 | AzureOpenAIConnector |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Yes | 1 | AzureOpenAIConnector |
| `AZURE_OPENAI_API_VERSION` | Yes | 1 | AzureOpenAIConnector |
| `AZURE_SEARCH_ENDPOINT` | Yes | 1 | AzureSearchConnector |
| `AZURE_SEARCH_API_KEY` | Yes | 1 | AzureSearchConnector |
| `AZURE_SEARCH_INDEX` | Yes | 1 | AzureSearchConnector |
| `ENTRA_TENANT_ID` | Yes | 2 | Auth middleware |
| `ENTRA_CLIENT_ID` | Yes | 2 | Auth middleware |
| `AUTH_DISABLED` | Dev only | 1 | Auth middleware |
| `TEAMS_WEBHOOK_URL` | Optional | 2 | TeamsConnector |
| `STORAGE_BACKEND` | Optional | 3 | Domain store factory |
| `COSMOS_CONNECTION_STRING` | UAT+ | 3 | CosmosStore |
| `COSMOS_DATABASE` | Optional | 3 | CosmosStore |
| `AZURE_TABLE_CONNECTION_STRING` | Alt | 3 | TableStore |
| `REDIS_URL` | Prod | 2+ | Checkpointer (Tier 1) |
| `LOG_LEVEL` | Optional | 1 | Logging config |
| `CORS_ORIGINS` | Optional | 1 | FastAPI CORS middleware |

---

## 6. Python Dependencies

```toml
# backend/pyproject.toml [project.dependencies]
[project]
name = "ai-ops-agent"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
    "openai>=1.30",
    "azure-search-documents>=11.4",
    "azure-data-tables>=12.5",
    "python-jose[cryptography]>=3.3",
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "langchain-openai>=0.2",
]

[project.optional-dependencies]
redis = [
    "langgraph-checkpoint-redis>=2.0",
    "redis>=5.0",
]
cosmos = [
    "motor>=3.3",
    "pymongo>=4.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
]
```

---

## 7. Coding Conventions

| Convention | Rule |
|---|---|
| **File header** | `from __future__ import annotations` as first line |
| **Naming** | `snake_case` for identifiers; `PascalCase` for classes/models |
| **ID prefixes** | `thr_`, `msg_`, `run_`, `out_`, `apr_`, `chg_` |
| **Imports** | Absolute imports only: `from app.models.domain import IncidentRecord` |
| **Logging** | `logger = logging.getLogger(__name__)` — no `print()` |
| **Type hints** | All function signatures fully typed; `Any` only when unavoidable |
| **Tests** | `pytest`, one file per feature area under `tests/`; `TestClient` for routes |
| **Linter** | Ruff (line-length=119, Python 3.11) |
| **Type checker** | MyPy (Python 3.11) |
| **Docstrings** | Google style, required on all public classes and functions |
