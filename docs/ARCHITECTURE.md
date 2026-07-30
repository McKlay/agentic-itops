# AI Operations Concierge — Architecture Documentation

> **Version:** 2.0 — Finalized technical specification  
> **Last updated:** 2026-04-28  
> **Replaces:** Initial scaffold architecture (v1.0)

> **⚠️ DEPRECATED:** This document is retained for historical reference only. The authoritative backend architecture documentation has moved to:
> - **[Backend Architecture (TSD Part 1)](../backend/docs/architecture/BACKEND-ARCHITECTURE.md)** — Overview & Architecture
> - **[Backend Services (TSD Part 2)](../backend/docs/architecture/BACKEND-SERVICES.md)** — Service Specifications
> - **[Frontend Architecture](../frontend/docs/architecture/FRONTEND-ARCHITECTURE.md)** — Frontend Overview
> - **[Frontend Components](../frontend/docs/architecture/COMPONENT-REFERENCE.md)** — Component Reference

---

## 1. Project Background

This project originated as a POC built with Microsoft Copilot Studio and Power Automate, demonstrated to an enterprise client. The client's production environment uses a proprietary agentic workflow framework that was not directly accessible to the implementation team. A dedicated engineering team adapted those architectural patterns with enterprise connectors, producing the current implementation (`falcon-ai-ops-agent`).

**Objective:** Demonstrate the features defined in the project timeline to obtain formal approval prior to transitioning to the client's target production framework. Upon approval, the connector layer (ServiceNow, Azure AI Search, Azure OpenAI) transfers directly — primarily the orchestration runtime changes.

---

## 2. Solution Overview

An AI-powered IT Operations chatbot deployed on Azure that assists enterprise end-users in resolving incidents and surfacing knowledge — with agents that create, update, and enrich ServiceNow tickets and Knowledge Articles on their behalf.

| Layer | Technology | Deployment Target |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript + Tailwind CSS 4 | Azure Static Web Apps |
| **Teams surface** | Teams Personal Tab (same React app, iframe) | Teams Admin Center |
| **Backend** | FastAPI + LangGraph (Python 3.11) | Azure App Service (Linux) |
| **AI engine** | Azure OpenAI — `gpt-5.3-chat` + `text-embedding-3-large` | Azure OpenAI Service |
| **Knowledge store** | Azure AI Search (hybrid: BM25 + vector) | Azure AI Search |
| **ITSM** | ServiceNow REST API | Developer instance → Production |
| **IaC** | Terraform | GitHub Actions |

---

## 3. Architecture Decision — Hierarchical ReAct with Quality Gate

### Why Not the Previous Architecture

The KnowledgeForge2 scaffold implemented a centralized supervised workflow engine:

| Gap | KnowledgeForge2 Reality |
|---|---|
| Agent autonomy | `execute()` returns deterministic outputs — no reasoning loop |
| Dynamic routing | Hardcoded `if/elif` keyword matching in `chat()` |
| Inter-agent communication | No shared context — agents start from scratch |
| Tool use | Tool lists are decorative strings, never invoked by LLM |
| Feedback loops | Linear playbooks with no retry or quality scoring |

### Selected Pattern — Hierarchical ReAct Loop

The architecture combines two proven enterprise patterns:

- **Architecture 2** (Hierarchical ReAct loop): Plan → Act → Observe → Critique cycle with explicit retry on low-quality outputs. The critic agent scores results and can force re-execution before surfacing to the user.
- **Architecture 3** (Shared context pipeline): A typed `RunContext` object flows between agents, accumulating evidence, recommendations, and tool results. Enterprise connectors are accessed exclusively through typed tool schemas.

```
User message
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  SUPERVISOR (Planner)                                           │
│  • LLM-driven intent classification                             │
│  • Goal decomposition into subtasks                             │
│  • Agent assignment based on capability matching                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ subtasks + RunContext
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTOR AGENTS (Act)                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │ Incident     │ │ Knowledge    │ │ Problem / RCA          │  │
│  │ Agent        │ │ Agent        │ │ Agent                  │  │
│  └──────────────┘ └──────────────┘ └────────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐                              │
│  │ Postmortem   │ │ Governance   │   Each agent:                │
│  │ Agent        │ │ Agent        │   • LLM reasoning loop       │
│  └──────────────┘ └──────────────┘   • Tool calling (ITSM,     │
│                                        Search, Telemetry)       │
│                                      • Appends to RunContext    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ observations
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  CRITIC (Quality Gate)                                          │
│  • Completeness check — all required fields populated           │
│  • Hallucination check — evidence supports conclusions          │
│  • Confidence scoring — threshold-based pass/retry/escalate     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ score ≥ 0.7 → pass to response formatter                │   │
│  │ score < 0.7 → retry (max 2 attempts) → HITL escalation  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ approved output
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  HUMAN-IN-THE-LOOP (Approval Gate)                              │
│  • AgentOutput with requires_approval=True → ApprovalTask       │
│  • Teams Adaptive Card notification                             │
│  • Approve/Reject via Command Center or Teams                   │
│  • Dispatch to ITSM connector on approval                       │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architecture Properties

| Property | Implementation |
|---|---|
| **Agent autonomy** | Each agent runs an LLM reasoning loop (ReAct: reason → tool call → observe → repeat) using Azure OpenAI function calling |
| **Dynamic routing** | Supervisor uses LLM intent classification returning `{agent, confidence, requires_approval}` — no hardcoded keyword matching |
| **Inter-agent communication** | Typed `RunContext` (Pydantic model) passed through the agent pipeline; each agent reads prior outputs and appends its own |
| **Tool use** | Connector methods exposed as OpenAI function-call schemas; LLM selects tools and parameters at runtime |
| **Feedback loops** | Critic agent scores quality; retry path feeds previous output + critique back to executor; user feedback updates retrieval weights |
| **Approval-first** | Every `AgentOutput` with `requires_approval=True` creates an `ApprovalTask`; no autonomous writes to production systems |

---

## 4. High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  USER LAYER                                                          │
│  ┌────────────────────────────┐  ┌─────────────────────────────┐    │
│  │  Browser (Static Web Apps) │  │  Teams Personal Tab (iframe)│    │
│  └─────────────┬──────────────┘  └──────────────┬──────────────┘    │
│                │  React 19 + Vite + Tailwind CSS 4                   │
│                │  3-panel: Sidebar | Workspace | Activity Feed       │
│                │  Auth: Entra ID SSO                                 │
└────────────────┼────────────────────────────────────────────────┬────┘
                 │ REST API (HTTPS + Bearer JWT)                  │
┌────────────────▼────────────────────────────────────────────────▼────┐
│  BACKEND  (Azure App Service — Python 3.11 / uvicorn)                │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                          │  │
│  │  ├── Auth middleware (Entra ID JWT validation)                 │  │
│  │  ├── Request logging middleware                                │  │
│  │  ├── Routes: /api/chat, /api/dashboard, /v1/threads, etc.     │  │
│  │  └── Error handlers (HTTPException, Validation, Unhandled)    │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │  Orchestration Layer (LangGraph StateGraph)                   │  │
│  │  ├── Supervisor node (intent → agent routing)                 │  │
│  │  ├── Executor agent nodes (tool-calling ReAct loops)          │  │
│  │  ├── Critic node (quality scoring + retry logic)              │  │
│  │  └── HITL interrupt node (approval gate)                      │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │  Tool Layer (OpenAI function-call schemas)                    │  │
│  │  ├── itsm_tools: lookup, create, update incident/KA/problem  │  │
│  │  ├── search_tools: hybrid_search, embed_query                 │  │
│  │  ├── telemetry_tools: get_signals, get_metrics                │  │
│  │  └── collaboration_tools: send_teams_notification             │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │  Connector Layer (typed clients with _live fallback)          │  │
│  │  ├── ServiceNowConnector   (httpx → SNOW REST API)            │  │
│  │  ├── AzureOpenAIConnector  (openai SDK)                       │  │
│  │  ├── AzureSearchConnector  (azure-search-documents SDK)       │  │
│  │  ├── TeamsConnector        (httpx → Incoming Webhook)         │  │
│  │  └── TelemetryConnector    (in-memory → App Insights)         │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │  Memory & State Layer (3-tier)                                │  │
│  │  ├── Tier 1: Conversation Memory (LangGraph checkpointing)    │  │
│  │  │   POC: MemorySaver / PROD: AsyncRedisSaver (Redis)         │  │
│  │  ├── Tier 2: Working Memory (RunContext — per-request)        │  │
│  │  └── Tier 3: Domain Store (DomainStoreInterface)              │  │
│  │      POC: InMemoryStore / PROD: CosmosStore (MongoDB API)     │  │
│  └────────────────────────────────────────────────────────────────┘  │
└───────┬──────────────┬──────────────┬──────────────┬────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
 ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
 │ ServiceNow │ │ Azure      │ │ Azure AI   │ │ Teams      │
 │ Dev/Prod   │ │ OpenAI     │ │ Search     │ │ Webhooks   │
 │ Instance   │ │            │ │ Index      │ │            │
 └────────────┘ └────────────┘ └────────────┘ └────────────┘
```

---

## 5. Backend Module Architecture

### Repository Structure

```
falcon-ai-ops-agent/
├── .github/
│   └── workflows/
│       ├── deploy-frontend.yml
│       ├── deploy-backend.yml
│       └── terraform.yml
├── frontend/                        # React + Vite + TS + Tailwind
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts           # Typed fetch wrapper + Bearer token
│   │   ├── components/
│   │   │   ├── layout/             # AppShell, Sidebar, ActivityFeed
│   │   │   ├── chat/               # Conversation, Composer, MessageBubble, ArtifactCard
│   │   │   ├── pages/              # Home, Incidents, Problems, Changes, Observability, Performance
│   │   │   └── shared/             # StatusPill, MetricTile, FeedCard, BarChart, DonutChart
│   │   ├── hooks/                   # useThread, useDashboard, useAuth, useSettings
│   │   ├── store/                   # Zustand: uiStore, chatStore, dashboardStore, settingsStore
│   │   ├── types/
│   │   │   └── api.ts              # TS interfaces mirroring Pydantic models
│   │   ├── App.tsx
│   │   ├── main.tsx                # microsoftTeams.initialize()
│   │   └── index.css               # @import "tailwindcss"
│   ├── staticwebapp.config.json
│   ├── vite.config.ts
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, lifespan, route registration
│   │   ├── config.py                # pydantic-settings: env var loading, typed config
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── domain.py            # IncidentRecord, ProblemRecord, ChangeRecord, KnowledgeArticle
│   │   │   ├── agent.py             # AgentOutput, RunContext (Tier 2 working memory), ToolCallResult
│   │   │   ├── chat.py              # OperationalThread, MessageRecord
│   │   │   ├── approval.py          # ApprovalTask, ApprovalDecision
│   │   │   ├── dashboard.py         # DashboardSnapshot, MetricPayload
│   │   │   └── auth.py              # CurrentUser, TokenClaims
│   │   ├── memory/                      # Tier 1 + LTM placeholder
│   │   │   ├── __init__.py
│   │   │   ├── checkpointer.py      # Checkpointer factory (MemorySaver → Redis cascade)
│   │   │   └── long_term.py         # LTM placeholder (BaseStore interface)
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseAgent: LLM reasoning loop + tool dispatch
│   │   │   ├── supervisor.py        # Supervisor: intent classification + agent routing
│   │   │   ├── critic.py            # Critic: quality scoring + retry/escalation
│   │   │   ├── incident.py          # IncidentAgent: triage + resolution drafts
│   │   │   ├── knowledge.py         # KnowledgeAgent: RAG retrieval + gap detection
│   │   │   ├── problem.py           # ProblemRcaAgent: RCA + corrective action plans
│   │   │   ├── postmortem.py        # PostmortemAgent: blameless postmortem drafts
│   │   │   └── governance.py        # GovernanceAgent: metrics + audit
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── registry.py          # Tool registry: name → schema + handler mapping
│   │   │   ├── itsm_tools.py        # lookup_incident, create_incident, update_incident, create_ka
│   │   │   ├── search_tools.py      # hybrid_search, get_article
│   │   │   ├── telemetry_tools.py   # get_signals, get_metrics
│   │   │   └── schemas.py           # OpenAI function-call JSON schemas
│   │   ├── connectors/
│   │   │   ├── __init__.py          # ConnectorBundle dataclass
│   │   │   ├── base.py              # ConnectorBase: _live flag, health_check(), fallback
│   │   │   ├── servicenow.py        # ServiceNowConnector: httpx → SNOW REST
│   │   │   ├── azure_openai.py      # AzureOpenAIConnector: chat_completion(), embed()
│   │   │   ├── azure_search.py      # AzureSearchConnector: hybrid_search()
│   │   │   └── teams.py             # TeamsConnector: Adaptive Card via webhook
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py      # LangGraph graph builder, node wiring, execution
│   │   │   ├── chat.py              # Conversational handler: history → LLM → response
│   │   │   ├── approval.py          # Approval lifecycle: create → review → dispatch
│   │   │   └── dashboard.py         # Dashboard snapshot aggregation + caching
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # Entra ID JWT validation, get_current_user dependency
│   │   │   └── logging.py           # Structured request/response logging
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py              # POST /api/chat
│   │   │   ├── threads.py           # /v1/threads CRUD
│   │   │   ├── assistants.py        # /v1/assistants
│   │   │   ├── dashboard.py         # GET /api/dashboard
│   │   │   ├── incidents.py         # GET /api/incidents/*
│   │   │   ├── approvals.py         # POST /api/approvals/{id}/decision
│   │   │   ├── settings.py          # GET/PUT /api/settings
│   │   │   └── health.py            # GET /healthz (public, no auth)
│   │   └── store/                       # Tier 3: Domain state persistence
│   │       ├── __init__.py
│   │       ├── base.py              # DomainStoreInterface (abstract)
│   │       ├── memory.py            # InMemoryStore + seed_store() for POC
│   │       ├── cosmos.py            # CosmosStore (Azure Cosmos DB MongoDB API)
│   │       ├── table.py             # TableStore (Azure Table Storage — alt)
│   │       └── factory.py           # create_domain_store() factory
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_chat.py
│   │   ├── test_orchestrator.py
│   │   ├── test_connectors.py
│   │   ├── test_approval.py
│   │   └── test_routes.py
│   ├── pyproject.toml
│   └── .env.example
├── infra/                            # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── terraform.tfvars.example
│   └── modules/
│       ├── resource-group/
│       │   └── main.tf
│       ├── app-service/
│       │   ├── main.tf
│       │   └── variables.tf
│       ├── static-web-app/
│       │   ├── main.tf
│       │   └── variables.tf
│       ├── openai/
│       │   ├── main.tf
│       │   └── variables.tf
│       ├── search/
│       │   ├── main.tf
│       │   └── variables.tf
│       ├── keyvault/
│       │   ├── main.tf
│       │   └── variables.tf
│       └── monitoring/
│           ├── main.tf
│           └── variables.tf
├── docs/
│   ├── ARCHITECTURE.md               # This document
│   ├── TECHNICAL-REFERENCE.md         # Detailed module specs, API contracts, Terraform
│   └── IMPLEMENTATION_CHECKLIST.md    # Phased implementation plan (separate)
├── .env.example
├── .gitignore
└── README.md
```

---

## 6. Authentication & Identity

### Entra ID SSO — Single Flow for Browser and Teams

```
User opens application (browser or Teams tab)
  │
  ▼
Azure Static Web Apps built-in auth (Entra ID provider)
  │  redirect → Microsoft login
  ▼
User authenticates with corporate email
  │  Entra ID issues JWT access token
  ▼
React app attaches token: Authorization: Bearer <token>
  │
  ▼
FastAPI middleware validates JWT (python-jose + JWKS)
  │  Extracts: name, email, oid
  ▼
CurrentUser injected via Depends(get_current_user)
  → Thread.initiated_by, ApprovalTask.decided_by, audit_log.actor
```

**Teams Personal Tab**: `microsoftTeams.initialize()` in `main.tsx`. Same Entra ID token — no re-authentication.

**ServiceNow access**: Users do **not** authenticate to SNOW through the chatbot. Deep-links are surfaced in chat responses. Users authenticate independently to their SNOW accounts.

**Local development**: `AUTH_DISABLED=true` env flag bypasses JWT validation. Never enabled in production.

| Role | Chatbot Login | SNOW Account Required? |
|---|---|---|
| End user | Entra ID SSO | No |
| KA approver | Entra ID SSO | Yes (dev instance) |
| Administrator | Entra ID SSO | Yes (admin) |

---

## 7. Data Flow

### Knowledge Ingestion

```
SharePoint (source PDFs) → Azure AI Search Indexer
  → PDF cracking → chunking → embedding (text-embedding-3-large)
  → Azure AI Search Index (hybrid: BM25 + vector)
```

### Chat Request Flow

```
User message → POST /api/chat
  → Auth middleware (validate JWT, extract CurrentUser)
  → ChatService.handle(message, thread_id, user)
  → Orchestrator.run(message, RunContext)
    → Supervisor node: LLM classifies intent → selects agent(s)
    → Executor agent node(s): LLM reasoning loop + tool calls
      → Tools invoke connectors (SNOW, AI Search, Telemetry)
    → Critic node: scores quality (completeness, grounding, confidence)
      → score ≥ threshold → format response
      → score < threshold → retry (max 2) → HITL escalation
    → If requires_approval → create ApprovalTask → notify Teams
  → Store MessageRecord (user + assistant)
  → Return response to frontend
```

### Approval Dispatch

```
POST /api/approvals/{id}/decision {decision: "approved"}
  → ApprovalService.decide(id, decision, user)
  → If approved: dispatch to ITSM connector (create KA / update incident)
  → Log audit event with actor identity
  → Notify via Teams webhook
```

---

## 8. Conversation History & LLM Context

### Storage

```
POST /v1/threads              → create session (returns thread_id)
POST /v1/threads/{id}/messages → append message
GET  /v1/threads/{id}/messages → retrieve history
```

**Conversation Memory (Tier 1):**

| Phase | Checkpointer | Persistence |
|---|---|---|
| POC | `MemorySaver` (in-process) | Lost on restart |
| Production | `AsyncRedisSaver` (Azure Cache for Redis) | Durable, sub-ms |

**Domain Store (Tier 3):**

| Phase | Storage | Cost |
|---|---|---|
| POC | InMemoryStore (seeded demo data) | None |
| UAT | CosmosStore (Azure Cosmos DB serverless) | ~$0.25/M RU |
| Alt | TableStore (Azure Table Storage) | ~$0.045/GB/month |

### LLM Context Construction

```python
messages_for_llm = [
    {"role": "system", "content": system_prompt},
    *[{"role": m.role, "content": m.content} for m in history[-20:]],  # sliding window
]
```

`MessageRecord.role` is typed as `"user" | "assistant" | "system"` — matches OpenAI format directly.

---

## 9. Feature Breakdown by Release

### Release 1 — Knowledge Foundation

| Feature | Description |
|---|---|
| Knowledge Retrieval | User query → RAG (AI Search hybrid) → cited KB response |
| Helpfulness Feedback | Thumbs up/down + comment per response → quality tracking |
| Incident-to-Knowledge Reporting | Agent detects gaps when <2 KAs match a resolved incident |
| AI-Driven Knowledge Creation | Gap detected → draft KA → approval queue → SNOW KB write |

### Release 2 — Chat Interface & Incident Automation

| Feature | Description |
|---|---|
| AI Chat Interface | Conversational UI in browser + Teams Personal Tab |
| Resolution Guidance | Incident context + KAs → LLM-generated step-by-step remediation |
| Automated Incident Update | User confirms resolution → agent updates SNOW (with approval) |

### Release 3 — Autonomous Record Creation & Measurement

| Feature | Description |
|---|---|
| Interaction Auto-Creation | Resolved chat → interaction record in SNOW |
| Incident Auto-Creation | Unresolved chat → new incident ticket with chat context |
| KA Enrichment | Batch review of existing KAs against recent incidents |
| KPI Dashboard | MTTR, adoption, resolution accuracy, hours saved |

### Release 4+ — Full Autonomy

| Feature | Description |
|---|---|
| Autonomous Resolution | High-confidence patterns auto-resolve without human approval |
| AI-Triggered Automation | Agent invokes runbooks and remediation scripts |

---

## 10. Azure Deployment Architecture

```
Resource Group: rg-ai-ops-agent
├── Static Web Apps            → React frontend (CDN + Entra ID auth)
├── App Registration           → Entra ID SSO (Client ID / Tenant ID)
├── App Service (Linux P1v3)   → FastAPI backend (uvicorn)
├── Azure OpenAI Service       → gpt-5.3-chat + text-embedding-3-large
├── Azure AI Search (Basic)    → ai-ops-knowledge-index (hybrid search)
├── Azure Cache for Redis      → Tier 1 conversation memory (LangGraph checkpoints)
├── Azure Cosmos DB (MongoDB)  → Tier 3 domain store (incidents, approvals, audit)
├── Key Vault                  → All secrets (referenced by App Service)
├── Application Insights       → Logging, metrics, distributed tracing
└── Log Analytics Workspace    → Backend for Application Insights
```

All infrastructure is provisioned via Terraform — see [TECHNICAL-REFERENCE.md](TECHNICAL-REFERENCE.md) § Terraform for module definitions.

---

## 11. Teams Integration

The React app runs identically in browser and Teams. Teams embeds it as an iframe (Personal Tab).

```typescript
// src/main.tsx
import * as microsoftTeams from "@microsoft/teams-js";
microsoftTeams.initialize();
```

**Approval notifications**: Adaptive Cards via Teams Incoming Webhook — single `httpx.post()` from the backend. No Bot Framework SDK required.

---

## 12. Connector Mapping

| Connector | Technology | Read/Write | Fallback |
|---|---|---|---|
| **ITSM** | ServiceNow REST API (httpx) | Read + Write | In-memory seeded data |
| **Knowledge** | Azure AI Search SDK (hybrid search) | Read only | In-memory stub |
| **LLM** | Azure OpenAI SDK (openai) | N/A | Deterministic fallback strings |
| **Notifications** | Teams Incoming Webhook (httpx) | Write only | Audit log only |
| **Telemetry** | Application Insights / in-memory | Read only | In-memory signals |

Every connector inherits from `ConnectorBase` and implements:
- `_live: bool` flag — toggled by health check or config
- `health_check() -> ConnectorHealth` — probed at startup and on demand
- Automatic fallback to in-memory data when `_live=False`

---

## 13. Key Design Principles

1. **Approval-first** — No agent action modifies production data without explicit human approval.
2. **Connector abstraction** — All external systems accessed through typed connectors. Switching from dev to production instance = configuration change only.
3. **Read from Search, Write to ITSM** — Azure AI Search is the read-optimized knowledge layer; ServiceNow is the write target.
4. **Graceful degradation** — Every connector falls back to in-memory data when its external service is unavailable.
5. **Auditability** — Every state-changing operation logs an event with timestamp, actor, and payload.
6. **Structured logging** — All modules use `logging.getLogger(__name__)` with JSON-formatted output. No `print()` statements.
7. **Type safety** — All function signatures fully typed. Pydantic models for all API contracts. TypeScript interfaces mirror Python models.

---

## 14. CI/CD

Two independent workflows with path-scoped triggers:

| Workflow | Trigger | Target |
|---|---|---|
| `deploy-frontend.yml` | `frontend/**` changes | Azure Static Web Apps |
| `deploy-backend.yml` | `backend/**` changes | Azure App Service |
| `terraform.yml` | `infra/**` changes | Terraform plan/apply |

Local development:
```bash
cd backend && uvicorn app.main:app --reload --port 8000   # Terminal 1
cd frontend && npm run dev                                  # Terminal 2 (proxies /api → :8000)
```

---

## 15. Supporting Documentation

| Document | Content |
|---|---|
| [TECHNICAL-REFERENCE.md](TECHNICAL-REFERENCE.md) | Module specifications, API contracts, Pydantic models, tool schemas, Terraform IaC, environment variables |
| [Backend Architecture](../backend/docs/architecture/BACKEND-ARCHITECTURE.md) | 3-tier memory architecture, corrected orchestrator with checkpointing, agent design, and framework alignment |
| [Frontend Architecture](../frontend/docs/architecture/FRONTEND-ARCHITECTURE.md) | React component architecture, state management, design tokens, deployment |
| [Component Reference](../frontend/docs/architecture/COMPONENT-REFERENCE.md) | Detailed component specs for all React components |
| [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) | Phased implementation plan with status tracking |
