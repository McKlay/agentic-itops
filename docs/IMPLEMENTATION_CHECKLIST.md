# Implementation Checklist

> Derived from the current source audit and the Architecture Document.
> Each item includes its current status and the files/resources affected.

---

## Phase 0 — Repository Restructuring

- [x] **0.1** Move `app/`, `tests/`, `connectors.toml`, `pyproject.toml`, `.env`, `.env.example` into a new `backend/` directory
- [x] **0.2** Create `frontend/` directory (React + Vite + TS + Tailwind scaffold — Phase 1)
- [x] **0.3** Update `pyproject.toml` paths (`[tool.setuptools.packages.find]`) to reflect `backend/app`
- [x] **0.4** Update `.gitignore` with frontend build artifacts (`frontend/node_modules/`, `frontend/dist/`)
- [x] **0.5** Add `docs/` at repo root (already in correct location — no move needed)
- [x] **0.6** Create `.github/workflows/deploy-frontend.yml` stub (triggers on `frontend/**`)
- [x] **0.7** Create `.github/workflows/deploy-backend.yml` stub (triggers on `backend/**`)

---

## Phase 1 — Environment & Secrets Setup

### ServiceNow PDI (New Instance)

- [ ] **1.1** Request a new Personal Developer Instance at [developer.servicenow.com](https://developer.servicenow.com) — sign up / log in → click **Request Instance** → wait for provisioning email (typically 5–15 minutes)
- [ ] **1.2** Activate the instance — log in as `admin` using the credentials from the provisioning email; set a permanent admin password
- [ ] **1.3** Create a dedicated service account user:
  - Navigate to **User Administration → Users → New**
  - Username: `svc_ai_ops` (or preferred name), Role: `itil` + `knowledge_admin`
  - Note the username and set a strong password
- [ ] **1.4** Grant the service account the following roles: `itil`, `knowledge_admin`, `rest_api_explorer`
- [ ] **1.5** Test REST API access with the service account credentials:
  ```
  GET https://<instance>.service-now.com/api/now/table/incident?sysparm_limit=1
  Authorization: Basic <base64(username:password)>
  ```
- [ ] **1.6** Test KB table write access:
  ```
  POST https://<instance>.service-now.com/api/now/table/kb_knowledge
  { "short_description": "API write test", "workflow_state": "draft" }
  ```
  Then delete the test record.
- [ ] **1.7** Update `.env` and `connectors.toml` with the new instance URL and service account credentials:
  ```
  SNOW_INSTANCE_URL=https://<your-instance>.service-now.com
  SNOW_SVC_USERNAME=svc_ai_ops
  SNOW_SVC_PASSWORD=<password>
  ```
- [x] **1.8** Update `connectors.toml` — remove hardcoded `base_url` and `username`; load solely from env vars (already handled by `app/__init__.py`, confirm `SNOW_INSTANCE_URL` is injected)
- [x] **1.9** Add `SNOW_INSTANCE_URL` injection to `load_config()` in `app/__init__.py` (currently only injects `SNOW_SVC_USERNAME` / `SNOW_SVC_PASSWORD`)
- [ ] **1.10** Log into the instance periodically — PDI instances hibernate after **10 days of inactivity** and are reclaimed after **30 days**; set a recurring calendar reminder

### Azure OpenAI

- [ ] **1.11** Provision Azure OpenAI resource (or confirm existing) in the resource group
- [ ] **1.12** Create deployment: `gpt-5.3-chat` (chat completions + agent structured output)
- [ ] **1.13** Create deployment: `text-embedding-3-large` (embeddings — superior retrieval vs ada-002)
- [ ] **1.14** Add env vars to `.env` and `.env.example`:
  ```
  AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
  AZURE_OPENAI_API_KEY=<key>
  AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.3-chat
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
  AZURE_OPENAI_API_VERSION=2025-01-01
  ```
- [ ] **1.15** Add `openai` to `pyproject.toml` dependencies

### Azure AI Search

- [ ] **1.16** Provision Azure AI Search resource (or confirm existing)
- [ ] **1.17** Create index (`ai-ops-knowledge-index`) with expected schema (title, body, embedding vector)
- [ ] **1.18** Configure indexer + skillset for SharePoint PDF ingestion (cracking → chunking → ada-002 embedding)
- [ ] **1.19** Add env vars to `.env` and `.env.example`:
  ```
  AZURE_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
  AZURE_SEARCH_API_KEY=<key>
  AZURE_SEARCH_INDEX=ai-ops-knowledge-index
  ```
- [ ] **1.20** Add `azure-search-documents` to `pyproject.toml` dependencies

### Microsoft Entra ID (Auth)

- [ ] **1.21** Create Azure App Registration — record Client ID and Tenant ID
- [ ] **1.22** Configure redirect URIs: Static Web Apps URL + `http://localhost:5173` (dev)
- [ ] **1.23** Expose API scope: `api://ai-ops-agent/Chat.Use`
- [ ] **1.24** Add env vars:
  ```
  ENTRA_TENANT_ID=<tenant>
  ENTRA_CLIENT_ID=<client-id>
  ```
- [ ] **1.25** Add `python-jose[cryptography]` and `msal` to `pyproject.toml` dependencies

### Teams Notifications

- [ ] **1.26** Create Teams Incoming Webhook in the target channel
- [ ] **1.27** Add env var: `TEAMS_WEBHOOK_URL=<url>`

### Key Vault (Production)

- [ ] **1.28** Provision Azure Key Vault and store all secrets
- [ ] **1.29** Configure App Service to reference Key Vault secrets via App Settings

---

## Phase 2 — Backend Connector Wiring

### Config Loader Updates (`app/__init__.py`)

- [ ] **2.1** Extend `load_config()` to inject Azure OpenAI, AI Search, Entra, and Teams env vars into the config dict
- [ ] **2.2** Update `connectors.toml` — add `[connectors.llm]`, `[connectors.search]`, `[connectors.auth]` sections

### Azure OpenAI Connector (NEW)

- [ ] **2.3** Create `app/services/llm.py` — wrapper around `openai.AzureOpenAI` client
  - `chat_completion(messages, model)` — calls chat completions API
  - `embed(text)` — calls embedding API
- [ ] **2.4** Add LLM connector to `ConnectorBundle` dataclass
- [ ] **2.5** Wire into `build_connectors()`

### Azure AI Search Connector (replace in-memory `KnowledgeConnector`)

- [ ] **2.6** Rewrite `KnowledgeConnector.search()` to call Azure AI Search (hybrid: vector + keyword)
  - Use `azure.search.documents.SearchClient`
  - Accept query string → embed via LLM connector → search index
  - Return top-K results with citations
- [ ] **2.7** Keep in-memory fallback behind a `_live` flag (same pattern as `ITSMConnector`)

### Teams Notification Connector (replace in-memory `CollaborationConnector`)

- [ ] **2.8** Update `CollaborationConnector.notify_approval_queue()` to POST Adaptive Card JSON to the webhook URL via `httpx.post()`
- [ ] **2.9** Keep in-memory audit fallback when `TEAMS_WEBHOOK_URL` is not set

### Chat / Conversation Handler (NEW)

- [ ] **2.10** Create `app/services/chat.py` — the conversational RAG handler:
  - Accept thread_id + user message
  - Retrieve thread history from `PlatformStore.get_messages()`
  - Build `messages` array: system prompt + sliding window (last 20)
  - Call LLM connector `chat_completion()`
  - Store assistant response as `MessageRecord`
  - Return response
- [ ] **2.11** Define system prompt constant (role, capabilities, constraints)
- [ ] **2.12** Add `/v1/threads/{thread_id}/chat` POST endpoint in `app/routes/messages.py`

---

## Phase 3 — Authentication Middleware

- [ ] **3.1** Create `app/middleware/auth.py` — FastAPI dependency that validates Entra ID JWT
  - Fetch JWKS from `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`
  - Validate `aud`, `iss`, `exp` claims
  - Extract `name`, `email` from token
- [ ] **3.2** Create `CurrentUser` Pydantic model (name, email, oid)
- [ ] **3.3** Add `get_current_user` dependency to all `/v1/*` and `/api/*` routes
- [ ] **3.4** Pass `user.email` as `initiated_by` on thread creation, run submission, and approval decisions
- [ ] **3.5** Keep `/healthz` and `/docs` as public (unauthenticated) routes
- [ ] **3.6** Add optional bypass for local development (env flag `AUTH_DISABLED=true`)

---

## Phase 4 — Agent LLM Integration

Currently, all agents return hardcoded/deterministic outputs. This phase wires them to the LLM.

- [ ] **4.1** Update `BaseAgent` to accept the LLM connector
- [ ] **4.2** Refactor `IncidentAgent.execute()` — build a prompt from incident + telemetry + history + KA data, call LLM, parse structured output
- [ ] **4.3** Refactor `KnowledgeAgent.execute()` — RAG pattern: embed query → search → synthesize answer via LLM
- [ ] **4.4** Refactor `ProblemRcaAgent.execute()` — generate RCA hypothesis and CAP via LLM
- [ ] **4.5** Refactor `BlamelessPostmortemAgent.execute()` — generate postmortem draft via LLM
- [ ] **4.6** Update `MonitoringGovernanceAgent` — optionally summarize metrics via LLM
- [ ] **4.7** Add structured output parsing (JSON mode or function calling) for consistent `AgentOutput` generation

---

## Phase 5 — Frontend Scaffold (React + Vite + TS + Tailwind)

- [ ] **5.1** Initialize `frontend/` — `npm create vite@latest . -- --template react-ts`
- [ ] **5.2** Install Tailwind CSS: `npm install -D tailwindcss @tailwindcss/vite`
- [ ] **5.3** Configure `vite.config.ts` — proxy `/api/*` and `/v1/*` to `localhost:8000`
- [ ] **5.4** Create typed API client (`src/api/client.ts`) — fetch wrapper with Bearer token
- [ ] **5.5** Create TypeScript interfaces (`src/types/api.ts`) mirroring Pydantic models
- [ ] **5.6** Set up Zustand store (`src/store/uiStore.ts`) — active nav, current session, view state
- [ ] **5.7** Build layout components:
  - `AppShell.tsx` — 3-panel grid (sidebar / workspace / activity feed)
  - `Sidebar.tsx` — navigation + session list
  - `ActivityFeed.tsx` — right rail live feed
- [ ] **5.8** Build chat components:
  - `Conversation.tsx` — message thread renderer
  - `Composer.tsx` — input + send button
  - `MessageBubble.tsx` — user/assistant bubble
  - `ArtifactCard.tsx` — rich card for RCA/KA outputs
- [ ] **5.9** Build page components:
  - `HomePage.tsx` — hero + quick actions
  - `IncidentsPage.tsx`, `ProblemsPage.tsx`, `ChangesPage.tsx`
  - `ObservabilityPage.tsx`, `PerformancePage.tsx`
- [ ] **5.10** Wire hooks: `useThread.ts`, `useDashboard.ts`, `useAuth.ts`
- [ ] **5.11** Add Teams SDK initialization in `main.tsx`: `microsoftTeams.initialize()`
- [ ] **5.12** Create `staticwebapp.config.json` for Azure SWA auth routes
- [ ] **5.13** Add `frontend/package.json` scripts: `dev`, `build`, `preview`

---

## Phase 6 — Release 1 Features (Knowledge Foundation)

- [ ] **6.1** Knowledge retrieval via chat (user query → RAG → cited KB response)
- [ ] **6.2** Feedback model + API endpoint (`POST /api/feedback`) — thumbs up/down + comment per response
- [ ] **6.3** Incident-to-Knowledge gap detection — `KnowledgeAgent` flags when <2 articles match a resolved incident
- [ ] **6.4** AI-driven KA creation flow: gap detected → draft KA → approval queue → `create_knowledge_article()` upon approval
- [ ] **6.5** End-to-end test: query → retrieval → feedback capture

---

## Phase 7 — Release 2 Features (Chat Interface & Incident Automation)

- [ ] **7.1** Chat interface end-to-end: user sends message → LLM response → stored in thread → rendered in UI
- [ ] **7.2** Step-by-step resolution guidance: incident context + KA → LLM-generated structured remediation guide
- [ ] **7.3** Automated incident update from chat: user confirms resolution → agent calls `update_incident()` (with approval gate)
- [ ] **7.4** Thread-to-incident linking: associate `OperationalThread.incident_id` when user discusses a specific ticket

---

## Phase 8 — Release 3 Features (Autonomous Creation & Measurement)

- [ ] **8.1** Auto-create interaction record in ServiceNow when a chat session resolves an issue
- [ ] **8.2** Auto-create incident ticket when chatbot cannot resolve (escalation detection)
- [ ] **8.3** KA enrichment batch mode — review existing KAs against recent incidents, draft updates
- [ ] **8.4** KPI dashboard API: extend `snapshot_metrics()` with MTTR, adoption, resolution accuracy, hours saved
- [ ] **8.5** Alpha user enablement — feature flags and user segmentation

---

## Phase 9 — Persistent Storage

- [ ] **9.1** Add `azure-data-tables` to `pyproject.toml`
- [ ] **9.2** Create `app/state_azure.py` — `AzureTableStore` implementing the same interface as `PlatformStore`
- [ ] **9.3** Add env var: `STORAGE_BACKEND=memory|azure_table`
- [ ] **9.4** Add connection string env var: `AZURE_TABLE_CONNECTION_STRING`
- [ ] **9.5** Swap `seed_store()` in `app/main.py` to return the appropriate store based on config

---

## Phase 10 — Deployment & CI/CD

- [ ] **10.1** Create Azure Resource Group (`rg-ai-ops-agent`)
- [ ] **10.2** Deploy App Service (Linux, Python 3.11) — configure App Settings from Key Vault
- [ ] **10.3** Deploy Azure Static Web Apps — link to `frontend/` build output
- [ ] **10.4** Configure CORS on App Service (allow SWA domain)
- [ ] **10.5** Finalize `deploy-frontend.yml` GitHub Actions workflow
- [ ] **10.6** Finalize `deploy-backend.yml` GitHub Actions workflow
- [ ] **10.7** Register Teams Personal Tab — create `manifest.json`, upload to Teams Admin Center
- [ ] **10.8** Validate end-to-end: browser → SWA → App Service → SNOW / AI Search / OpenAI

---

## Current State Summary

| Component | Status | Notes |
|---|---|---|
| FastAPI backend scaffold | **Done** | Runs locally, all routes functional |
| Pydantic models | **Done** | Full model set: Incident, Problem, Change, KA, Thread, Message, Run, Approval |
| In-memory `PlatformStore` | **Done** | Seeded demo data, audit log, metrics |
| ITSM Connector (ServiceNow) | **Done** | Dual-mode: live REST + in-memory fallback |
| KA create/get/publish | **Done** | Wired through `ITSMConnector` |
| Agent framework | **Done** | 5 agents (Incident, Knowledge, Problem, Postmortem, Governance) — all deterministic |
| Supervisor/orchestration | **Done** | Triage, postmortem, change-draft, RCA playbooks |
| Approval workflow | **Done** | Create → review → decide → dispatch to SNOW |
| Command Center HTML | **Done** | Jinja2 template, functional dashboard |
| Thread/Message/Run API | **Done** | Full CRUD at `/v1/*` endpoints |
| Tests | **Partial** | 4 tests (dashboard + runs) |
| Azure OpenAI integration | **Not started** | No `openai` dependency or code |
| Azure AI Search integration | **Not started** | `KnowledgeConnector` is in-memory only |
| Auth (Entra ID) | **Not started** | No JWT validation, no user identity flow |
| Teams webhook notifications | **Not started** | `CollaborationConnector` logs to audit only |
| React frontend | **Not started** | Only Jinja2 HTML exists |
| CI/CD pipelines | **Not started** | No `.github/workflows/` |
| Persistent storage | **Not started** | In-memory only |
