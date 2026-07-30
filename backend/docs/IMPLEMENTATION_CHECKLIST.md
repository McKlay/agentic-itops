# Backend Implementation Checklist

> Scaffolds the full backend structure per BACKEND-ARCHITECTURE.md / BACKEND-SERVICES.md.  
> Priority: **knowledge_agent** first, incident_agent second. Other agents deferred.  
> Updated as features are implemented.

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-04 | CM Sarte | Initial backend implementation checklist |

---

## Source References

Code snippets, interfaces, and module specs in this checklist are derived from the following architecture documents. Section cross-references are noted per checklist item where applicable.

| Document | Location | Content |
|----------|----------|---------|
| **Backend Architecture (TSD Part 1)** | [BACKEND-ARCHITECTURE.md](architecture/BACKEND-ARCHITECTURE.md) | Five-layer architecture, three-tier memory design, LangGraph orchestration, Terraform IaC |
| **Backend Services (TSD Part 2)** | [BACKEND-SERVICES.md](architecture/BACKEND-SERVICES.md) | Per-module service specs, connector interfaces, agent logic, route definitions |

> **Key section anchors used throughout this checklist:**
> - `ARCH §3` — Five-layer architecture diagram
> - `ARCH §4` — Three-tier memory design (Tier 1/2/3)
> - `ARCH §5` — Orchestrator deep dive + lifespan entry point
> - `ARCH §6` — Agent architecture + framework migration pattern
> - `SVC §1` — Service inventory + DI patterns
> - `SVC §2` — Orchestrator interface + graph topology + compilation
> - `SVC §3` — Chat service processing flow
> - `SVC §4` — Agent layer (BaseAgent, SupervisorAgent, CriticAgent, HITL gate)
> - `SVC §5` — Tool layer (ToolRegistry, schemas, dispatch flow)
> - `SVC §6` — Connector layer (ConnectorBase, all connectors, ConnectorBundle)
> - `SVC §7` — Store layer (DomainStoreInterface, InMemoryStore, CosmosStore, factory)
> - `SVC §8` — Memory layer (checkpointer factory, LTM placeholder)
> - `SVC §9` — Middleware (auth, structured logging)
> - `SVC §10` — API routes
> - `SVC §12.1` — Pydantic model reference table
> - `SVC §12.2` — `Settings` configuration reference

---

## Phase 1 — Project Setup & Configuration
> _Ref: `SVC §1.2` (tech stack), `SVC §12.2` (Settings reference), `ARCH §5.1` (repository structure)_

- [x] **1.1** Create `backend/pyproject.toml` — project metadata, dependencies (`fastapi`, `uvicorn`, `pydantic[settings]`, `httpx`, `openai`, `azure-search-documents`, `langgraph`, `langchain-core`, `python-jose[cryptography]`), optional extras (`[redis]`, `[cosmos]`, `[dev]`, `[all]`)
- [x] **1.2** Create `backend/.env.example` — all env vars with placeholder values (no secrets)
- [x] **1.3** Create `backend/app/__init__.py` — empty package init
- [x] **1.4** Create `app/config.py` — `Settings(BaseSettings)` with all env vars per §12.2 of BACKEND-SERVICES.md; `model_config = {"env_file": ".env", "case_sensitive": False}`

---

## Phase 2 — Pydantic Models
> _Ref: `SVC §12.1` (model inventory), `ARCH §4.2` (RunContext / Tier 2 working memory)_

- [x] **2.1** Create `app/models/__init__.py`
- [x] **2.2** Create `app/models/auth.py` — `CurrentUser` (user_id, email, name, roles)
- [x] **2.3** Create `app/models/domain.py` — `IncidentRecord`, `ProblemRecord`, `ChangeRecord`, `KnowledgeArticle`
- [x] **2.4** Create `app/models/agent.py` — `RunContext` (LangGraph state schema / Tier 2), `AgentOutput`, `ToolCallResult`; `messages` field uses `Annotated[list[AnyMessage], add_messages]`
- [x] **2.5** Create `app/models/chat.py` — `OperationalThread`, `MessageRecord`, `ChatRequest`, `ChatResponse`
- [x] **2.6** Create `app/models/approval.py` — `ApprovalTask`, `ApprovalDecision`
- [x] **2.7** Create `app/models/dashboard.py` — `DashboardSnapshot`, `MetricPayload`

---

## Phase 3 — Store Layer (Tier 3 — Domain State)
> _Ref: `SVC §7` (DomainStoreInterface, InMemoryStore, CosmosStore, factory), `ARCH §4.3` (Tier 3 design)_

- [x] **3.1** Create `app/store/__init__.py`
- [x] **3.2** Create `app/store/base.py` — `DomainStoreInterface(ABC)` with all abstract methods (threads, incidents, outputs, approvals, audit, settings, snapshot)
- [x] **3.3** Create `app/store/memory.py` — `InMemoryStore` implementing the interface; `seed()` method populates demo data (incidents, KAs, threads)
- [x] **3.4** Create `app/store/factory.py` — `create_domain_store(settings)` factory returning `InMemoryStore` for POC
- [x] **3.5** Stub `app/store/cosmos.py` — `CosmosStore` class with `raise NotImplementedError` bodies
- [x] **3.6** Stub `app/store/table.py` — `TableStore` class with `raise NotImplementedError` bodies

---

## Phase 4 — Memory Layer (Tier 1 — Conversation Checkpointing)
> _Ref: `SVC §8` (checkpointer factory, LTM placeholder), `ARCH §4.1` (Tier 1 design + checkpointer priority cascade)_

- [x] **4.1** Create `app/memory/__init__.py`
- [x] **4.2** Create `app/memory/checkpointer.py` — `get_checkpointer(settings)` with priority cascade (Redis → MemorySaver fallback); module-level `_GLOBAL_CHECKPOINTER` singleton
- [x] **4.3** Stub `app/memory/long_term.py` — `LongTermMemoryStore(BaseStore)` placeholder with `NotImplementedError`

---

## Phase 5 — Connector Layer
> _Ref: `SVC §6` (ConnectorBase, all connectors, ConnectorBundle), `SVC §1.3` (fallback pattern)_

- [x] **5.1** Create `app/connectors/__init__.py` — `ConnectorBundle` dataclass + `build_connectors(settings)` factory
- [x] **5.2** Create `app/connectors/base.py` — `ConnectorBase(ABC)` with `_live` flag, `_require_live()`, `health_check()` abstract; `ConnectorHealth` model
- [x] **5.3** Create `app/connectors/azure_openai.py` — `AzureOpenAIConnector`: `chat_completion(messages, tools, temperature)`, `embed(text) -> list[float]`; init `AsyncAzureOpenAI` client when env vars present, fallback otherwise
- [x] **5.4** Create `app/connectors/azure_search.py` — `AzureSearchConnector`: `search(query, vector, top_k)` using `SearchClient`; hybrid BM25+vector; in-memory fallback with seeded KAs
- [x] **5.5** Stub `app/connectors/servicenow.py` — `ServiceNowConnector` with `get_incident`, `create_incident`, `update_incident`; in-memory fallback for POC
- [x] **5.6** Stub `app/connectors/teams.py` — `TeamsConnector` with `send_card()`; audit-log-only fallback

---

## Phase 6 — Tool Layer
> _Ref: `SVC §5` (ToolRegistry, schemas, tool inventory, dispatch flow)_

- [x] **6.1** Create `app/tools/__init__.py`
- [x] **6.2** Create `app/tools/registry.py` — `ToolRegistry` class: `register(name, handler, schema)`, `get_schemas(tool_names)`, `execute(name, arguments)`
- [x] **6.3** Create `app/tools/schemas.py` — OpenAI function-call JSON schemas for all tools (`hybrid_search`, `get_article`, `lookup_incident`, `create_incident`, `update_incident`, `get_signals`, `get_metrics`, `send_teams_notification`)
- [x] **6.4** Create `app/tools/search_tools.py` — `hybrid_search(query, top_k)` and `get_article(article_id)` handlers wired to `AzureSearchConnector`
- [x] **6.5** Stub `app/tools/itsm_tools.py` — handlers for `lookup_incident`, `create_incident`, `update_incident`
- [x] **6.6** Stub `app/tools/telemetry_tools.py` — `get_signals`, `get_metrics`
- [x] **6.7** Stub `app/tools/collaboration_tools.py` — `send_teams_notification`

---

## Phase 7 — Agent Layer (Knowledge Agent Priority)
> _Ref: `SVC §4` (BaseAgent, SupervisorAgent, CriticAgent, HITL gate), `ARCH §6` (agent architecture + framework migration)_

- [x] **7.1** Create `app/agents/__init__.py`
- [x] **7.2** Create `app/agents/base.py` — `BaseAgent(ABC)` with ReAct loop: `run(state) -> dict`, `_build_messages(state)`, `_parse_output(response, state)`; `MAX_STEPS=5`
- [x] **7.3** Create `app/agents/supervisor.py` — `SupervisorAgent`: LLM intent classification → sets `intent`, `selected_agents`, `requires_approval` on `RunContext`
- [x] **7.4** Create `app/agents/knowledge.py` — `KnowledgeAgent`: RAG retrieval via `hybrid_search` + `get_article` tools; gap detection when <2 articles match; synthesizes answer with citations
- [x] **7.5** Create `app/agents/critic.py` — `CriticAgent`: LLM quality scoring; returns `critic_score`, `critic_feedback`, increments `retry_count` if below threshold
- [x] **7.6** Stub `app/agents/incident.py` — `IncidentAgent` with basic structure, not yet wired to LLM
- [x] **7.7** Stub `app/agents/problem.py` — `ProblemRcaAgent`
- [x] **7.8** Stub `app/agents/postmortem.py` — `PostmortemAgent`
- [x] **7.9** Stub `app/agents/governance.py` — `GovernanceAgent`

---

## Phase 8 — Orchestrator & Chat Service
> _Ref: `SVC §2` (Orchestrator interface, graph topology, compilation, execution flow), `SVC §3` (ChatService processing flow), `ARCH §5.2–5.3`_

- [x] **8.1** Create `app/services/__init__.py`
- [x] **8.2** Create `app/services/orchestrator.py` — `Orchestrator` class: `initialize()`, `run(message, thread_id, user)`, `resume(thread_id, decision)`, `get_thread_state(thread_id)`; builds `StateGraph(RunContext)` with nodes: `supervisor`, agent nodes, `critic`, `hitl_gate`, `response_formatter`; compiles with checkpointer; conditional edges per §2.3–2.5 of BACKEND-SERVICES.md
- [x] **8.3** Create `app/services/chat.py` — `ChatService`: `handle(message, thread_id, user) -> ChatResponse`; stores user/assistant `MessageRecord`s, invokes orchestrator, returns response
- [x] **8.4** Stub `app/services/approval.py` — approval lifecycle: create → review → dispatch
- [x] **8.5** Stub `app/services/dashboard.py` — `DashboardService` with `snapshot()` aggregation

---

## Phase 9 — Middleware
> _Ref: `SVC §9` (auth dependency, JWT validation, structured logging middleware)_

- [x] **9.1** Create `app/middleware/__init__.py`
- [x] **9.2** Create `app/middleware/auth.py` — `get_current_user(request) -> CurrentUser` dependency; JWKS fetch + JWT validation (`aud`, `iss`, `exp`); `AUTH_DISABLED=true` bypass for dev
- [x] **9.3** Create `app/middleware/logging.py` — `StructuredLoggingMiddleware`: logs method, path, status, duration_ms, user_id per request

---

## Phase 10 — API Routes
> _Ref: `SVC §10` (route summary, chat endpoint, thread state, approval decision, health check)_

- [x] **10.1** Create `app/routes/__init__.py`
- [x] **10.2** Create `app/routes/health.py` — `GET /healthz` (unauthenticated); returns connector health statuses
- [x] **10.3** Create `app/routes/chat.py` — `POST /api/chat` with `ChatRequest` → `ChatResponse`; depends on orchestrator, store, user
- [x] **10.4** Create `app/routes/threads.py` — `POST /v1/threads`, `GET /v1/threads/{id}`, `POST /v1/threads/{id}/runs/wait`, `GET /v1/threads/{id}/state`, `GET /v1/threads/{id}/history`
- [x] **10.5** Create `app/routes/dashboard.py` — `GET /api/dashboard` returning `DashboardSnapshot`
- [x] **10.6** Create `app/routes/incidents.py` — `GET /api/incidents`, `GET /api/incidents/{id}`
- [x] **10.7** Create `app/routes/approvals.py` — `POST /api/approvals/{id}/decision`
- [x] **10.8** Create `app/routes/settings.py` — `GET/PUT /api/settings`
- [x] **10.9** Stub `app/routes/assistants.py` — `GET /v1/assistants`

---

## Phase 11 — Application Entry Point
> _Ref: `ARCH §5.3` (lifespan entry point), `SVC §1.3` (DI pattern, error handlers)_

- [x] **11.1** Create `app/main.py` — `FastAPI` app with `@asynccontextmanager` lifespan; initializes `Settings`, `create_domain_store`, `build_connectors`, `Orchestrator`; registers routers, CORS, error handlers, logging middleware
- [x] **11.2** Verify local startup: `cd backend && uvicorn app.main:app --reload --port 8000`
- [x] **11.3** Verify `/healthz` returns connector statuses
- [x] **11.4** Verify `/docs` renders OpenAPI spec with all routes

---

## Phase 12 — Knowledge Agent End-to-End Validation
> _Ref: `SVC §4.3` (KnowledgeAgent tools), `SVC §5.5` (hybrid search dispatch), `ARCH §4.4` (memory tier interaction flow)_

- [x] **12.1** Verify `POST /api/chat` with a knowledge query routes to `knowledge_agent` via supervisor
- [x] **12.2** Verify `hybrid_search` tool is invoked by the agent with correct query
- [x] **12.3** Verify Azure AI Search connector returns ranked results (or fallback KAs)
- [x] **12.4** Verify agent synthesizes cited answer and returns `AgentOutput` with `requires_approval=False`
- [x] **12.5** Verify `ChatResponse` includes message text + `agent_outputs` array
- [x] **12.6** Verify `MessageRecord`s persisted in domain store for thread history
- [x] **12.7** Verify critic scores the output ≥ 0.7 and routes to `response_formatter` → END

---

## Phase 13 — Tests
> _Ref: `SVC §11.5` (testing conventions — pytest, pytest-asyncio, TestClient)_

- [ ] **13.1** Create `tests/conftest.py` — `TestClient` fixture, mock `Settings`, seeded `InMemoryStore`
- [ ] **13.2** Create `tests/test_health.py` — health endpoint returns 200
- [ ] **13.3** Create `tests/test_chat.py` — chat endpoint processes a knowledge query end-to-end
- [ ] **13.4** Create `tests/test_connectors.py` — each connector returns fallback data when `_live=False`
- [ ] **13.5** Create `tests/test_store.py` — `InMemoryStore` CRUD operations
- [ ] **13.6** Create `tests/test_knowledge_agent.py` — agent calls `hybrid_search`, synthesizes answer, returns `AgentOutput`

---

## Deferred (Future Phases)

| Item | Depends On |
|------|-----------|
| `IncidentAgent` full LLM wiring | Phases 1–11 complete |
| `ProblemRcaAgent`, `PostmortemAgent`, `GovernanceAgent` | Incident agent stable |
| `CosmosStore` implementation | Azure Cosmos DB provisioned |
| `AsyncRedisSaver` checkpointing | Azure Cache for Redis provisioned |
| Approval dispatch to ServiceNow | ServiceNow PDI configured |
| Teams Adaptive Card notifications | Teams webhook created |
| Long-term memory (`LongTermMemoryStore`) | Cross-session patterns identified |
| Observability (`app/observability/`) | Application Insights provisioned |
| Terraform IaC (`infra/`) | Azure subscription access |
