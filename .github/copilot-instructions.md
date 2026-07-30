# GitHub Copilot Instructions — AI Operations Concierge

## Project Overview

An **approval-first, enterprise agentic IT Operations platform** built on a Pygentic-style architecture. The backend is a FastAPI application that orchestrates AI agents to triage incidents, retrieve knowledge, draft RCA reports, and manage ServiceNow records. All agent-generated actions require explicit human approval before any data is written to production systems. The frontend is a React + Tailwind SPA that provides a chat interface for interacting with the AI assistant, viewing incident timelines, and managing approvals. The system integrates with Azure OpenAI for LLM capabilities, Azure AI Search for knowledge retrieval, and ServiceNow as the ITSM backend. Authentication is handled via Entra ID JWTs. The architecture emphasizes modular connectors, a unified in-memory store with audit logging, and strict separation of concerns between read (Search) and write (ITSM) operations.

---

**Local development:**
```bash
# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev   # Vite proxies /api/* and /v1/* → localhost:8000
```

---

## Tech Stack & Best Practices

### Python / FastAPI (Backend)

- **Python 3.11**, FastAPI ≥ 0.115, Pydantic v2, uvicorn
- Use `from __future__ import annotations` at the top of every module
- All models inherit from `pydantic.BaseModel`; use `Field(default_factory=...)` for mutable defaults
- FastAPI dependency injection (`Depends(...)`) for auth, store, and connectors — never import `app.state` globals directly in routes
- Pull `store`, `connectors`, and `supervisor` from `request.app.state` in route handlers
- Use `@asynccontextmanager` lifespan for all startup/shutdown logic — no `@app.on_event`
- Prefer `httpx` for all outbound HTTP calls (already a dependency); use `httpx.AsyncClient` for async routes
- All exceptions flow through the handlers registered in `main.py` — raise `HTTPException` or `KeyError`; never return raw 500s
- Every new connector class must implement a `_live: bool` flag and an in-memory fallback — match the `ITSMConnector` pattern

### Azure OpenAI

- Client: `openai.AzureOpenAI` (sync) or `openai.AsyncAzureOpenAI` (async preferred)
- Always pass `api_version` from config — do not hardcode
- Temperature: `0.2` for structured agent outputs; `0.7` for conversational chat
- Sliding window: pass last 20 `MessageRecord` objects as the `messages` array; prepend system prompt
- Model: **`gpt-4.1`** for all completions (chat + agent structured output) — strong instruction-following, native function calling, deployment name `gpt-4.1`
- Embeddings: **`ka-embedding-model`** (backed by `text-embedding-3-small`) — deployment name used in Azure AI Search hybrid queries
- Wrap in `app/services/llm.py` — expose `chat_completion(messages, temperature)` and `embed(text) -> list[float]`

### Azure AI Search

- Client: `azure.search.documents.SearchClient`
- Use **hybrid search** (vector + keyword) — pass both `search_text` and `vectors` in the query
- Vector field: embed the query via `llm.embed()` before searching
- Return top-5 results by default; include `@search.score` as the citation confidence
- Keep the in-memory `KnowledgeConnector.search()` fallback active when `AZURE_SEARCH_ENDPOINT` is not set

### Authentication (Entra ID / JWT)

- Validate JWTs in `app/middleware/auth.py` using `python-jose`
- Fetch JWKS from: `https://login.microsoftonline.com/{ENTRA_TENANT_ID}/discovery/v2.0/keys`
- Required claims: `aud` == `ENTRA_CLIENT_ID`, `iss` contains `ENTRA_TENANT_ID`, `exp` not expired
- Extract `name` and `preferred_username` (email) into a `CurrentUser` Pydantic model
- Inject via `Depends(get_current_user)` — do not parse tokens in route handlers directly
- `AUTH_DISABLED=true` env flag bypasses validation in local development only — never in production

### ServiceNow REST API

- Base URL from `SNOW_INSTANCE_URL` env var — never hardcode
- All writes use Basic Auth with the dedicated service account (`SNOW_SVC_USERNAME` / `SNOW_SVC_PASSWORD`)
- Table endpoints: `incident` for tickets, `kb_knowledge` for knowledge articles
- Always set `sysparm_fields` on GET calls to limit response payload
- KB articles created with `workflow_state: "review"` — not `"draft"` or `"published"` directly
- Use `incident_url()` and `ka_url()` helpers to generate direct ServiceNow browser links

### Teams Incoming Webhook

- Single `httpx.post(TEAMS_WEBHOOK_URL, json=card_payload)` call — no Bot Framework SDK
- Adaptive Card schema v1.4; include title, description, and an `Action.OpenUrl` button
- Fallback: if `TEAMS_WEBHOOK_URL` is not set, log the event to `PlatformStore.audit_log` only

### React Frontend (Phase 5+)

- **Vite + React + TypeScript + Tailwind CSS** — do not use Create React App
- Tailwind via `@tailwindcss/vite` plugin — not PostCSS
- State management: **Zustand** only — no Redux, no Context API for global state
- API calls: typed `fetch` wrapper in `src/api/client.ts`; always attach `Authorization: Bearer <token>`
- TypeScript interfaces in `src/types/api.ts` must mirror Pydantic model field names exactly
- All component files use `.tsx`; all hook files use `.ts`
- `microsoftTeams.initialize()` called once in `main.tsx` — not in components
- Proxy `/api/*` and `/v1/*` to `localhost:8000` in `vite.config.ts` for local development

### CI/CD (GitHub Actions)

- Two independent workflows: `deploy-frontend.yml` (paths: `frontend/**`) and `deploy-backend.yml` (paths: `backend/**`)
- Backend workflow: `pip install -e .` from `backend/` working directory, then `azure/webapps-deploy@v3`
- Frontend workflow: `Azure/static-web-apps-deploy@v1` with `app_location: "frontend"`, `output_location: "dist"`, `skip_api_build: true`
- Secrets via GitHub Actions secrets (sourced from Azure Key Vault in production)

---

## Key Design Principles (Never Violate)

1. **Approval-first**: Every `AgentOutput` with `requires_approval=True` must flow through an `ApprovalTask` before `dispatch_approved_output()` pushes anything to ServiceNow.
2. **No direct secrets in code**: All credentials come from env vars only. `connectors.toml` contains no secrets.
3. **Connector abstraction**: External systems are only accessed through connector classes in `app/services/connectors.py`. No `httpx` calls in route handlers or agents.
4. **Read from Search, Write to ITSM**: Azure AI Search is the knowledge read layer. ServiceNow is the write target. Do not cross these concerns.
5. **In-memory fallback**: Every connector must degrade gracefully when its external service is unconfigured. Check `self._live` before making outbound calls.
6. **Auditability**: Every state-changing operation must call `store.log_event(kind, payload)`. Never silently mutate store state.

---

## Environment Variables (Full Reference)

| Variable | Required | Used In |
|---|---|---|
| `SNOW_INSTANCE_URL` | Yes (live mode) | `app/__init__.py` → `ITSMConnector` |
| `SERVICENOW_USERNAME` | Yes (live mode) | `app/__init__.py` → `ITSMConnector` |
| `SERVICENOW_PASSWORD` | Yes (live mode) | `app/__init__.py` → `ITSMConnector` |
| `AZURE_OPENAI_ENDPOINT` | Phase 2+ | `LLMConnector` |
| `AZURE_OPENAI_API_KEY` | Phase 2+ | `LLMConnector` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Phase 2+ | `LLMConnector` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Phase 2+ | `LLMConnector` |
| `AZURE_OPENAI_API_VERSION` | Phase 2+ | `LLMConnector` |
| `AZURE_SEARCH_ENDPOINT` | Phase 2+ | `KnowledgeConnector` |
| `AZURE_SEARCH_API_KEY` | Phase 2+ | `KnowledgeConnector` |
| `AZURE_SEARCH_INDEX_NAME` | Phase 2+ | `KnowledgeConnector` |
| `ENTRA_TENANT_ID` | Phase 3+ | `auth.py` middleware |
| `ENTRA_CLIENT_ID` | Phase 3+ | `auth.py` middleware |
| `TEAMS_WEBHOOK_URL` | Phase 2+ | `CollaborationConnector` |
| `STORAGE_BACKEND` | Phase 9+ | `app/main.py` store factory |
| `AZURE_TABLE_CONNECTION_STRING` | Phase 9+ | `AzureTableStore` |
| `AUTH_DISABLED` | Dev only | `auth.py` middleware |

---

## Conventions

- **File headers**: `from __future__ import annotations` is the first line of every `.py` file
- **Naming**: `snake_case` for all Python identifiers; `PascalCase` for Pydantic models and classes
- **ID prefixes**: `thr_` threads, `msg_` messages, `run_` runs, `out_` outputs, `apr_` approvals, `chg_` changes
- **Tests**: `pytest`, one file per feature area under `tests/`; use `TestClient` from `fastapi.testclient`
- **No print statements**: use `logging.getLogger(__name__)` for any diagnostic output
- **Type hints**: all function signatures must be fully typed; use `Any` only where genuinely unavoidable
