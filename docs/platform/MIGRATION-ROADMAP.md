# Migration Roadmap — From Current App to Reusable Platform

> Status: draft roadmap  
> Purpose: provide a practical phased path from the current implementation to the target reusable platform

---

## 1. Migration philosophy

Do not rewrite the working application.

Instead, refactor in thin vertical slices while preserving current behavior.

The current implementation already has useful modular boundaries. The roadmap should strengthen those boundaries and introduce platform concepts gradually.

---

## 2. Current maturity estimate

| Area | Current maturity | Notes |
|---|---|---|
| FastAPI app structure | Good | clear app factory, routes, services |
| Agent orchestration | Good POC | LangGraph-based orchestration exists |
| Connector abstraction | Good starting point | needs provider interfaces above concrete connectors |
| Store abstraction | Good starting point | needs tenant-aware partitioning |
| Runtime config | Basic | mostly global env config |
| Tenancy | Missing | no explicit tenant/instance context |
| Observability | Basic | request logs and stub telemetry only |
| Evaluation | Missing | no formal eval datasets or regression harness |
| Policy layer | Partial | approval-first exists but policy is not separated |
| Multi-cloud infra | Not implemented | architecture can prepare for it |
| Admin/control plane | Missing | future capability |

---

## 3. Phase 0 — Document and stabilize current implementation

Goal: avoid losing current working behavior.

Tasks:

- keep current architecture docs updated
- add platform planning docs
- document current routes, services, agents, connectors, and stores
- ensure tests cover existing chat, approval, connector fallback, and health behavior
- identify hardcoded product names and provider assumptions

Exit criteria:

- current app behavior is documented
- basic tests pass
- refactor targets are clear

---

## 4. Phase 1 — Introduce platform context

Goal: add tenant/instance awareness without changing deployment model.

Tasks:

- create `TenantContext` model
- create `TenantResolver`
- add `tenant_id` and `instance_id` to settings
- pass context through chat service and orchestrator
- add tenant fields to threads, approvals, audit, and outputs where appropriate
- keep default tenant for local/dev mode

Recommended first default:

```text
tenant_id = default
instance_id = ai-ops-local
```

Exit criteria:

- app still works as before
- every run has tenant and instance context
- persisted records can be partitioned later

---

## 5. Phase 2 — Externalize prompts and runtime settings

Goal: remove hardcoded persona and organization assumptions from agent code.

Tasks:

- create prompt files under `config/prompts/ai_ops`
- introduce `PromptRegistry`
- add prompt version identifiers
- move product/persona text to config
- make critic threshold and max retries configurable
- add prompt pack ID to run envelope

Exit criteria:

- agent prompts can be changed without editing Python files
- prompt versions are visible in traces/logs
- current behavior remains reproducible with default prompt pack

---

## 6. Phase 3 — Provider interfaces above connectors

Goal: turn concrete connectors into swappable providers.

Tasks:

- define `LlmProvider`
- define `SearchProvider`
- define `ITSMProvider`
- define `NotificationProvider`
- migrate existing Azure OpenAI, Azure Search, ServiceNow, and Teams connectors behind those interfaces
- introduce provider registry
- keep current Azure provider bindings as defaults

Exit criteria:

- agents/tools depend on provider interfaces
- Azure remains functional
- mock providers support tests

---

## 7. Phase 4 — Observability run envelope

Goal: capture agent behavior consistently.

Tasks:

- add `run_id` and `trace_id`
- create `AgentRunEnvelope`
- create `RunObserver`
- create `NoopTraceCollector`
- emit run start/end events
- capture selected agents, tool calls, retries, critic score, approval status, and final response metadata
- store summaries in audit or run table

Exit criteria:

- every agent run produces a normalized run envelope
- no external observability vendor is required yet
- later Phoenix/LangSmith/internal-platform integration is straightforward

---

## 8. Phase 5 — Policy and governance layer

Goal: centralize decisions about allowed actions.

Tasks:

- introduce `PolicyEngine`
- define tool metadata such as read/write, approval required, sensitivity
- enforce policy before tool execution
- enforce policy before dispatching approved outputs
- make approval thresholds configurable
- add policy decisions to trace envelope

Exit criteria:

- side-effect actions are gated by policy
- policies can vary by tenant/instance
- decisions are auditable

---

## 9. Phase 6 — Evaluation foundation

Goal: add repeatable quality testing.

Tasks:

- create `evals/` folder
- add small knowledge Q&A dataset
- add incident triage cases
- add tool-selection test cases
- create simple graders for citation presence, tool choice, and answer relevance
- add optional CI workflow for eval regression

Exit criteria:

- prompts and agent changes can be regression-tested
- quality is measured, not only manually inspected

---

## 10. Phase 7 — External observability adapters

Goal: integrate with optional tools.

Tasks:

- implement Phoenix adapter or LangSmith adapter first
- keep adapter optional through config
- add OpenTelemetry-friendly span model if practical
- add token/cost metrics
- document internal runtime and observability adapter requirements as details become known

Exit criteria:

- traces can be exported to at least one external backend
- core code remains backend-agnostic

---

## 11. Phase 8 — Infrastructure foundation

Goal: create Azure Terraform first while preserving future multi-cloud structure.

Tasks:

- create `infra/modules/azure`
- define shared output contract
- add environment overlays
- deploy backend runtime, frontend, secrets, search, storage, cache, and monitoring
- keep AWS/GCP folder placeholders or design docs until needed

Exit criteria:

- one environment can be provisioned repeatably
- outputs map cleanly into app config
- future provider modules have a known contract

---

## 12. Phase 9 — Control-plane/admin capabilities

Goal: manage tenant and instance setup more easily.

Tasks:

- create tenant registry store
- create instance registry store
- expose admin APIs
- add admin UI only when APIs stabilize
- manage provider bindings and feature flags

Exit criteria:

- new assistant instances can be configured through metadata
- manual code changes are no longer required for basic instance setup

---

## 13. Suggested priority order

Highest value first:

1. `TenantContext`
2. prompt externalization
3. provider interfaces
4. run envelope and observer
5. policy engine
6. evaluation datasets
7. external tracing adapter
8. Terraform Azure foundation
9. admin/control plane

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| Overengineering too early | implement no-op/default versions first |
| Breaking current POC | refactor behind interfaces while preserving defaults |
| Vendor lock-in | use provider adapters and normalized models |
| Weak tenant isolation | add tenant IDs to data models early |
| Poor agent quality visibility | add run envelope and evals early |
| Unclear internal platform contracts | design adapters without assuming final APIs |

---

## 15. First concrete implementation slice

The first refactor slice should be intentionally small:

1. Add `platform/tenancy/context.py`.
2. Add a default `TenantContext` resolver.
3. Add `tenant_id`, `instance_id`, and `environment` to settings.
4. Pass context to `ChatService` and `Orchestrator`.
5. Add `run_id` to each orchestration run.
6. Emit a simple run summary log.

This creates the foundation for all later platform work without forcing a rewrite.
