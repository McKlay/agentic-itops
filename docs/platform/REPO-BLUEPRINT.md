# Repository Blueprint — Future Reusable Platform Structure

> Status: draft blueprint  
> Purpose: propose a future source layout for a reusable multi-tenant agentic AI platform

---

## 1. Guiding idea

The future repository should separate reusable platform capabilities from tenant-specific configuration and provider-specific implementations.

The current repository already has useful folders such as `backend/app/agents`, `backend/app/tools`, `backend/app/connectors`, and `backend/app/store`. The target blueprint evolves those into clearer platform modules.

---

## 2. Proposed top-level structure

```text
falcon-ai-ops-agent/
├── apps/
│   ├── web/                         # React user-facing assistant UI
│   └── admin/                       # Future admin/control-plane UI
├── backend/
│   ├── app/                         # FastAPI composition root
│   ├── platform/                    # Reusable platform runtime modules
│   ├── solutions/                   # Domain-specific assistant packages
│   ├── tests/
│   └── pyproject.toml
├── config/
│   ├── tenants/                     # Tenant and instance definitions
│   ├── prompts/                     # Prompt packs and versions
│   ├── policies/                    # Policy definitions
│   ├── providers/                   # Provider binding examples
│   └── environments/                # Local/dev/test/prod overlays
├── infra/
│   ├── modules/
│   │   ├── azure/
│   │   ├── aws/
│   │   ├── gcp/
│   │   └── shared/
│   ├── environments/
│   │   ├── dev/
│   │   ├── test/
│   │   └── prod/
│   └── README.md
├── evals/
│   ├── scenarios/
│   ├── graders/
│   └── reports/
├── docs/
│   ├── platform/
│   └── runbooks/
├── tools/
│   ├── scripts/
│   └── generators/
└── .github/
    └── workflows/
```

This is a target structure, not a required immediate migration.

---

## 3. Backend target structure

```text
backend/
├── app/
│   ├── main.py                      # FastAPI composition root
│   ├── lifespan.py                  # Startup/shutdown composition
│   ├── dependencies.py              # FastAPI dependency providers
│   ├── routes/                      # HTTP routers
│   └── middleware/                  # HTTP middleware
├── platform/
│   ├── tenancy/                     # TenantContext, resolver, registry
│   ├── config/                      # Settings loaders and validation
│   ├── orchestration/               # Graph runtime and run service
│   ├── agents/                      # Base agent abstractions and registry
│   ├── prompts/                     # Prompt registry and template rendering
│   ├── tools/                       # Tool registry, schemas, execution wrapper
│   ├── providers/                   # Provider interfaces and adapters
│   │   ├── llm/
│   │   ├── search/
│   │   ├── identity/
│   │   ├── notification/
│   │   ├── storage/
│   │   ├── secrets/
│   │   └── observability/
│   ├── policy/                      # Policy engine and rule evaluation
│   ├── observability/               # Run observers, trace collectors, metrics
│   ├── evaluation/                  # Eval recorder and online/offline scoring
│   ├── events/                      # Event bus and background jobs
│   ├── store/                       # Store interfaces and implementations
│   └── security/                    # Redaction, auth helpers, permission checks
├── solutions/
│   └── ai_ops/
│       ├── agents/                  # Incident, knowledge, RCA agents
│       ├── tools/                   # ITSM/search/telemetry domain tools
│       ├── prompts/                 # AI Ops prompt pack
│       ├── policies/                # AI Ops policy defaults
│       └── models/                  # AI Ops domain models
└── tests/
```

---

## 4. Why introduce `platform/` and `solutions/`

### `platform/`

Contains reusable capabilities that should apply to any agentic assistant.

Examples:

- tenant context
- orchestration runtime
- provider abstraction
- observability hooks
- policy engine
- prompt registry
- tool execution wrapper

### `solutions/`

Contains domain-specific behavior.

Examples:

- AI Operations agents
- ITSM-specific tools
- RCA prompts
- governance dashboards
- ServiceNow domain models

This separation prevents the reusable platform from being permanently tied to one use case.

---

## 5. Provider folder pattern

```text
platform/providers/
├── llm/
│   ├── base.py                      # LlmProvider interface
│   ├── azure_openai.py              # Azure OpenAI implementation
│   ├── openai.py                    # Optional OpenAI implementation
│   ├── bedrock.py                   # Future AWS implementation
│   ├── vertex.py                    # Future GCP implementation
│   └── internal_runtime.py          # Future internal runtime adapter if applicable
├── search/
│   ├── base.py
│   ├── azure_ai_search.py
│   ├── opensearch.py
│   ├── vertex_search.py
│   └── internal_knowledge.py        # Future internal knowledge adapter if applicable
├── observability/
│   ├── base.py
│   ├── noop.py
│   ├── phoenix.py
│   ├── langsmith.py
│   ├── internal_observability.py
│   └── internal_runtime.py
└── identity/
    ├── base.py
    ├── entra.py
    ├── cognito.py
    └── google_identity.py
```

Each provider implementation should satisfy the same platform interface so agents do not care which backend is active.

---

## 6. Configuration target structure

```text
config/
├── tenants/
│   ├── default.yaml
│   ├── enterprise-ai-ops.yaml
│   └── example-client.yaml
├── prompts/
│   ├── ai_ops/
│   │   ├── supervisor.v1.md
│   │   ├── knowledge.v1.md
│   │   └── critic.v1.md
│   └── shared/
│       └── safety.v1.md
├── policies/
│   ├── default.yaml
│   ├── approval-first.yaml
│   └── read-only-demo.yaml
├── providers/
│   ├── azure.yaml
│   ├── aws.yaml
│   ├── gcp.yaml
│   ├── internal-runtime.yaml
│   └── internal-knowledge.yaml
└── environments/
    ├── local.yaml
    ├── dev.yaml
    ├── test.yaml
    └── prod.yaml
```

Configuration should be layered:

1. platform defaults
2. environment overlay
3. tenant settings
4. instance settings
5. runtime overrides where allowed

---

## 7. Evaluation folder

```text
evals/
├── datasets/
│   ├── ai_ops_knowledge_questions.jsonl
│   ├── incident_triage_cases.jsonl
│   └── approval_decision_cases.jsonl
├── scenarios/
│   ├── knowledge_retrieval.yaml
│   ├── incident_creation.yaml
│   └── rca_generation.yaml
├── graders/
│   ├── citation_grounding.py
│   ├── tool_selection.py
│   └── response_quality.py
└── reports/
```

The `evals/` folder is important because reusable agentic platforms need regression testing beyond normal unit tests.

---

## 8. Infrastructure folder

```text
infra/
├── modules/
│   ├── shared/
│   │   ├── naming/
│   │   └── tags/
│   ├── azure/
│   │   ├── app_runtime/
│   │   ├── static_site/
│   │   ├── identity/
│   │   ├── llm/
│   │   ├── search/
│   │   ├── storage/
│   │   ├── secrets/
│   │   └── observability/
│   ├── aws/
│   │   ├── app_runtime/
│   │   ├── static_site/
│   │   ├── identity/
│   │   ├── llm/
│   │   ├── search/
│   │   ├── storage/
│   │   ├── secrets/
│   │   └── observability/
│   └── gcp/
│       ├── app_runtime/
│       ├── static_site/
│       ├── identity/
│       ├── llm/
│       ├── search/
│       ├── storage/
│       ├── secrets/
│       └── observability/
└── environments/
    ├── dev/
    ├── test/
    └── prod/
```

Use provider-specific Terraform modules behind a shared output contract instead of trying to make one identical module work across all clouds.

---

## 9. Migration from current folders

| Current folder | Target destination |
|---|---|
| `backend/app/agents` | split between `platform/agents` and `solutions/ai_ops/agents` |
| `backend/app/tools` | split between `platform/tools` and `solutions/ai_ops/tools` |
| `backend/app/connectors` | migrate to `platform/providers/*` |
| `backend/app/store` | migrate to `platform/store` |
| `backend/app/services/orchestrator.py` | migrate to `platform/orchestration` |
| `backend/app/middleware/auth.py` | evolve into `platform/providers/identity` plus middleware wrapper |
| `frontend` | migrate or alias to `apps/web` |
| future admin UI | create `apps/admin` |
| future Terraform | create `infra/modules/{azure,aws,gcp}` |

---

## 10. Beginner-friendly rule of thumb

If code is reusable across many assistants, put it under `platform/`.

If code only makes sense for AI Operations, ServiceNow triage, RCA, governance, or knowledge articles, put it under `solutions/ai_ops/`.

If code only changes per team, put it under `config/`.

If code provisions cloud infrastructure, put it under `infra/`.
