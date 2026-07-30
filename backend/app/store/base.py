from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.models.agent import AgentOutput
from app.models.approval import ApprovalDecision, ApprovalTask
from app.models.chat import OperationalThread
from app.models.dashboard import DashboardSnapshot
from app.models.domain import IncidentRecord


# ---------------------------------------------------------------------------
# Supporting models only used by the store layer
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    """Immutable record written to the audit log on every state-changing operation."""

    event_id: str                                      # evt_ prefix
    kind: str                                          # e.g. "incident.upserted"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    user_id: str | None = None


class RuntimeSettings(BaseModel):
    """User-configurable runtime settings persisted in the Domain Store.

    Distinct from ``app.config.Settings`` (which is environment/deployment config).
    These are preferences changeable at runtime via the settings UI.
    """

    agent_persona: str = "SwiftAssist AI"
    default_temperature: float = 0.7
    max_history_messages: int = 20
    critic_threshold: float = 0.7
    max_retries: int = 2
    notifications_enabled: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Marker base classes for stub implementations (no abstract methods added)
# ---------------------------------------------------------------------------

class CosmosStoreBase:
    """Marker — CosmosStore must implement ``initialize()`` and ``_ensure_indexes()``."""


class TableStoreBase:
    """Marker — TableStore must implement ``initialize()``."""


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class DomainStoreInterface(ABC):
    """Abstract interface for Tier 3 domain state persistence.

    Implementations:
    - ``InMemoryStore`` — POC, dict-backed, seeded with demo data
    - ``CosmosStore``   — Azure Cosmos DB (MongoDB API), UAT / Production
    - ``TableStore``    — Azure Table Storage, cost-optimised alternative

    **Key principle:** every write method must call ``log_event()`` to maintain
    an immutable audit trail.  Never silently mutate state.
    """

    # --- Threads ---
    @abstractmethod
    async def add_thread(self, thread: OperationalThread) -> None: ...

    @abstractmethod
    async def get_thread(self, thread_id: str) -> OperationalThread | None: ...

    @abstractmethod
    async def list_threads(self, user_id: str | None = None) -> list[OperationalThread]: ...

    # --- Incidents ---
    @abstractmethod
    async def upsert_incident(self, record: IncidentRecord) -> None: ...

    @abstractmethod
    async def get_incident(self, incident_id: str) -> IncidentRecord | None: ...

    @abstractmethod
    async def list_incidents(self, filters: dict | None = None) -> list[IncidentRecord]: ...

    # --- Agent outputs ---
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

    # --- Audit log ---
    @abstractmethod
    async def log_event(self, kind: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    async def get_audit_log(self, limit: int = 100) -> list[AuditEvent]: ...

    # --- Runtime settings ---
    @abstractmethod
    async def get_settings(self) -> RuntimeSettings: ...

    @abstractmethod
    async def save_settings(self, settings: RuntimeSettings) -> None: ...

    # --- Dashboard aggregation ---
    @abstractmethod
    async def snapshot(self) -> DashboardSnapshot: ...
