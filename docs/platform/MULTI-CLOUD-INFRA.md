# Multi-Cloud Infrastructure Strategy

> Status: draft design  
> Purpose: define how Terraform and deployment architecture can support Azure first, then AWS and GCP

---

## 1. Key clarification

Terraform can provision Azure, AWS, and GCP resources. That does not automatically make the application cloud-agnostic.

There are two separate concerns:

1. Infrastructure portability: can the platform be deployed to different clouds?
2. Runtime portability: can the app use equivalent services across providers?

The target platform should support both eventually, but it should do so through clear provider-specific modules and runtime adapters.

---

## 2. Recommended strategy

Use a shared infrastructure contract with cloud-specific Terraform implementations.

Do not try to force one identical Terraform module to work across all providers.

Instead:

```text
infra/modules/
├── shared/
├── azure/
├── aws/
└── gcp/
```

Each cloud module should expose similar outputs, even if the internal resources differ.

---

## 3. Common platform capabilities 

Every cloud deployment should provide these logical capabilities:

| Capability | Azure example | AWS example | GCP example |
|---|---|---|---|
| Backend runtime | App Service / Container Apps | ECS Fargate / App Runner / EKS | Cloud Run / GKE |
| Frontend hosting | Static Web Apps / Storage + CDN | S3 + CloudFront / Amplify | Cloud Storage + CDN / Firebase Hosting |
| Identity | Entra ID | Cognito / external OIDC | Google Identity / Identity Platform |
| LLM | Azure OpenAI | Bedrock | Vertex AI |
| Search/RAG | Azure AI Search | OpenSearch / Kendra | Vertex AI Search / Matching Engine |
| Secrets | Key Vault | Secrets Manager | Secret Manager |
| Runtime state | Cosmos DB / Table Storage | DynamoDB / Aurora | Firestore / Cloud SQL |
| Cache/checkpoint | Azure Cache for Redis | ElastiCache Redis | Memorystore Redis |
| Observability | App Insights / Azure Monitor | CloudWatch / X-Ray | Cloud Logging / Trace |
| Object storage | Blob Storage | S3 | Cloud Storage |

---

## 4. Infrastructure module layout

```text
infra/
├── modules/
│   ├── shared/
│   │   ├── naming/
│   │   ├── tagging/
│   │   └── validation/
│   ├── azure/
│   │   ├── app_runtime/
│   │   ├── frontend/
│   │   ├── identity/
│   │   ├── llm/
│   │   ├── search/
│   │   ├── storage/
│   │   ├── cache/
│   │   ├── secrets/
│   │   └── observability/
│   ├── aws/
│   │   ├── app_runtime/
│   │   ├── frontend/
│   │   ├── identity/
│   │   ├── llm/
│   │   ├── search/
│   │   ├── storage/
│   │   ├── cache/
│   │   ├── secrets/
│   │   └── observability/
│   └── gcp/
│       ├── app_runtime/
│       ├── frontend/
│       ├── identity/
│       ├── llm/
│       ├── search/
│       ├── storage/
│       ├── cache/
│       ├── secrets/
│       └── observability/
├── environments/
│   ├── dev/
│   │   ├── azure.tfvars
│   │   ├── aws.tfvars
│   │   └── gcp.tfvars
│   ├── test/
│   └── prod/
└── README.md
```

---

## 5. Shared output contract

Each cloud implementation should emit equivalent logical outputs.

Example:

```text
app_base_url
frontend_url
identity_issuer
identity_audience
llm_endpoint
llm_model_or_deployment
search_endpoint
search_index_name
secrets_reference
storage_connection_reference
cache_connection_reference
observability_endpoint
```

The application should consume these through environment variables, secret references, or generated config profiles.

---

## 6. Environment overlays

Use environment overlays for:

- local
- dev
- test
- prod
- demo
- tenant-specific deployments

Each overlay should define:

- cloud provider
- region
- SKU/sizing
- provider bindings
- secret references
- tenant or instance identifiers
- observability settings

---

## 7. Deployment topology options

### Option A: one deployment per tenant

Simplest operational model.

Pros:

- strong isolation
- simpler provider config
- easier security boundary
- easier cost allocation

Cons:

- more deployments to manage
- more duplicated infrastructure

Best for early enterprise deployments.

### Option B: shared multi-tenant deployment

One backend serves multiple tenants.

Pros:

- shared infrastructure
- lower cost at scale
- easier central updates

Cons:

- requires stronger runtime tenancy
- more complex secrets/config resolution
- stricter data partitioning required

Best after platform maturity increases.

### Option C: hybrid

Shared control plane with separate data-plane deployments per tenant.

Pros:

- central management
- strong runtime isolation
- good enterprise fit

Cons:

- more architecture complexity

Best long-term target.

---

## 8. CI/CD strategy

Recommended workflows:

```text
.github/workflows/
├── backend-test.yml
├── frontend-test.yml
├── infra-plan.yml
├── infra-apply.yml
├── deploy-backend.yml
├── deploy-frontend.yml
├── eval-regression.yml
└── release.yml
```

Add matrix support later:

- environment matrix
- cloud provider matrix
- tenant/instance matrix

Example dimensions:

```text
provider: azure | aws | gcp
environment: dev | test | prod
solution: ai_ops | future_solution
tenant: shared_enterprise | client_a
```

---

## 9. Secrets strategy

Do not store secrets in Terraform state if avoidable.

Recommended pattern:

- Terraform creates secret containers and access policies
- secrets are injected separately through secure CI/CD or enterprise secret workflows
- application receives secret references or managed identity access

Provider examples:

- Azure Key Vault
- AWS Secrets Manager
- GCP Secret Manager
- internal enterprise secret platform if available

---

## 10. Observability infrastructure

Observability infra should be optional and pluggable.

Baseline:

- cloud-native logs and metrics
- application structured logs
- health checks

Advanced:

- Phoenix deployment or managed endpoint
- LangSmith project configuration
- OpenTelemetry collector
- internal platform integration endpoint

---

## 11. Practical recommendation

Start with Azure Terraform because it matches the current implementation.

But structure the IaC from day one as:

- provider-specific modules
- shared output contract
- environment overlays
- optional observability modules
- tenant/instance-aware variables

This avoids needing to restructure later when AWS/GCP support is requested.
