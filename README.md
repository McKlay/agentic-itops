# SwiftAssist AI — Operations Concierge

> **Approval-first, enterprise agentic IT Operations platform for enterprise teams**  
> Built by the AI Operations Concierge Team

---

## Overview

SwiftAssist AI is a conversational AI assistant for enterprise IT operations. It triages incidents, retrieves knowledge, generates Root Cause Analysis (RCA) reports, and manages ServiceNow records — all behind an explicit **human-in-the-loop (HITL) approval gate**. No agent autonomously writes to production systems.

**Core principles:**
- Every agent action with side effects requires explicit human approval before dispatch
- Connector abstraction — external systems accessed only through typed connector classes
- Read from Azure AI Search (knowledge), write to ServiceNow (ITSM) — concerns are separated
- Every state-changing operation is logged to the audit trail

---

## Capabilities

| Capability | Description |
|---|---|
| **Incident Triage** | AI severity classification, resolution drafting, ServiceNow integration |
| **Knowledge Retrieval** | RAG via Azure AI Search — hybrid BM25 + vector search over KB articles |
| **Root Cause Analysis** | Multi-agent RCA pipeline with evidence gathering and corrective action plans |
| **Blameless Postmortems** | Structured postmortem generation with review agendas |
| **Alert Governance** | Monitoring rule drafts and alert tuning recommendations |
| **Approval Workflow** | HITL approval via LangGraph `interrupt()` / `resume()` |

---

## Architecture

### Backend — Five-Layer FastAPI Application

```
LAYER 1  FastAPI             Auth middleware · request logging · route handlers
LAYER 2  Orchestration       LangGraph StateGraph: Supervisor → Executor(s) → Critic → HITL gate
LAYER 3  Tools               OpenAI function-call schemas dispatching to connectors
LAYER 4  Connectors          Typed clients with _live flag + in-memory fallback
LAYER 5  Memory & State      Three-tier memory (see below)
```

**Three-Tier Memory Design:**

| Tier | Purpose | POC | Production |
|---|---|---|---|
| **1 — Conversation** | LangGraph checkpointing per thread | `MemorySaver` (in-process) | `AsyncRedisSaver` → Azure Cache for Redis |
| **2 — Working** | Transient per-request `RunContext` (Pydantic) | same | same |
| **3 — Domain Store** | Persistent ITSM records, approvals, audit log | `InMemoryStore` | `CosmosStore` → Azure Cosmos DB (MongoDB API) |

### Frontend — React SPA / Teams Personal Tab

A single React SPA that runs identically in the browser and as a Microsoft Teams Personal Tab. Three-panel grid layout: Sidebar · Workspace · Activity Feed.

**View routing** is state-driven via Zustand (`currentView`) — no React Router.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend runtime** | Python 3.11, FastAPI ≥ 0.115, Pydantic v2, uvicorn |
| **Orchestration** | LangGraph ≥ 0.2, LangChain Core ≥ 0.3 |
| **LLM / Embeddings** | Azure OpenAI — `gpt-5.3-chat` · `text-embedding-3-large` |
| **Knowledge** | Azure AI Search (hybrid BM25 + vector, top-5 results) |
| **ITSM** | ServiceNow REST API (via `httpx`) |
| **Auth** | Microsoft Entra ID JWT (`python-jose`) |
| **Notifications** | Microsoft Teams Adaptive Card webhook |
| **Frontend** | React 19, Vite 8, TypeScript 6, Tailwind CSS 4, Zustand 5 |
| **Deployment** | Azure App Service (backend) · Azure Static Web Apps (frontend) |
| **IaC** | Terraform (9 modules) |

---

## Project Structure

```
falcon-ai-ops-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, route registration
│   │   ├── config.py            # pydantic-settings — all env vars
│   │   ├── models/              # Pydantic models (domain, agent, chat, approval, auth)
│   │   ├── memory/              # Tier 1: checkpointer factory (MemorySaver → Redis)
│   │   ├── agents/              # LangGraph nodes: supervisor, critic, executor agents
│   │   ├── tools/               # OpenAI function-call schemas + ToolRegistry
│   │   ├── connectors/          # ServiceNow, AzureOpenAI, AzureSearch, Teams
│   │   ├── services/            # orchestrator, chat, approval, dashboard
│   │   ├── store/               # Tier 3: InMemoryStore (POC) / CosmosStore (prod)
│   │   ├── middleware/          # Entra ID JWT auth, structured JSON logging
│   │   └── routes/              # /api/chat, /api/dashboard, /v1/threads, /healthz, …
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/client.ts        # Typed fetch wrapper with Bearer token
    │   ├── components/          # layout/, chat/, pages/, shared/, modals/
    │   ├── hooks/               # useThread, useDashboard, useAuth, useSettings
    │   ├── store/               # uiStore, chatStore, dashboardStore, settingsStore
    │   ├── types/api.ts         # TS interfaces mirroring backend Pydantic models
    │   ├── App.tsx
    │   └── main.tsx             # Teams init + React root
    ├── staticwebapp.config.json # SWA Entra ID auth routes
    ├── vite.config.ts
    └── package.json
```

---

## Local Development

**Prerequisites:** Python 3.11, Node.js 20+

```bash
# 1. Backend
cd backend
cp .env.example .env          # fill in credentials
pip install -e .
uvicorn app.main:app --reload --port 8000

# 2. Frontend  (separate terminal)
cd frontend
npm install
npm run dev                   # Vite dev server :5173, proxies /api/* → :8000
```

Set `AUTH_DISABLED=true` in `backend/.env` to bypass JWT validation locally.

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `SNOW_INSTANCE_URL` | Live mode | ServiceNow base URL |
| `SNOW_SVC_USERNAME` / `SNOW_SVC_PASSWORD` | Live mode | ServiceNow service account |
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` | Phase 2+ | Azure OpenAI |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Phase 2+ | Chat model deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Phase 2+ | Embedding model deployment name |
| `AZURE_OPENAI_API_VERSION` | Phase 2+ | API version string |
| `AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_API_KEY` | Phase 2+ | Azure AI Search |
| `AZURE_SEARCH_INDEX` | Phase 2+ | Search index name |
| `ENTRA_TENANT_ID` / `ENTRA_CLIENT_ID` | Phase 3+ | Entra ID JWT validation |
| `TEAMS_WEBHOOK_URL` | Phase 2+ | Teams Adaptive Card notifications |
| `AUTH_DISABLED` | Dev only | Bypass JWT validation (`true`) |

See `backend/.env.example` for the full reference.

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Send chat message, receive assistant response |
| `/api/dashboard` | GET | Full dashboard snapshot |
| `/api/incidents/overview` | GET | Filtered / paginated incidents |
| `/api/approvals/{id}/decision` | POST | Submit HITL approval decision |
| `/v1/threads` | POST | Create conversation thread |
| `/v1/threads/{id}/runs/wait` | POST | Run graph (or resume from interrupt) |
| `/v1/threads/{id}/state` | GET | Inspect current graph state |
| `/v1/threads/{id}/history` | GET | Full checkpoint history |
| `/api/settings` | GET / PUT | Load / save runtime settings |
| `/healthz` | GET | Health check |

---

## Deployment

**Backend** → Azure App Service (Linux, Python 3.11), deployed via `.github/workflows/deploy-backend.yml`.

**Frontend** → Azure Static Web Apps, deployed via `.github/workflows/deploy-frontend.yml`.

Both workflows are path-filtered and triggered independently on pushes to `main`.

---

## Framework Alignment

This platform is designed for migration to a target enterprise agentic workflow framework:

- Checkpointer cascade mirrors the target framework's priority resolution pattern
- Agent composition follows a role-playing agent plus supervisor agent pattern
- Domain store uses MongoDB API aligned with Cosmos-style store abstractions
- Tool schemas use OpenAI function-call format (same as LangChain `@tool`)
