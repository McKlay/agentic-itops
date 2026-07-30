from __future__ import annotations

import logging
from typing import Any

from app.models.agent import AgentOutput
from app.models.approval import ApprovalDecision, ApprovalTask
from app.models.chat import OperationalThread
from app.models.dashboard import DashboardSnapshot
from app.models.domain import IncidentRecord
from app.store.base import AuditEvent, CosmosStoreBase, DomainStoreInterface, RuntimeSettings

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED_MSG = (
    "CosmosStore is not yet implemented. "
    "Provision an Azure Cosmos DB (MongoDB API) instance and set COSMOS_CONNECTION_STRING."
)


class CosmosStore(CosmosStoreBase, DomainStoreInterface):
    """Production store — Azure Cosmos DB with MongoDB API.

    Uses Motor async MongoDB driver aligned with the PyGentic CosmosDBCollection pattern.
    Collections: threads, incidents, agent_outputs, approvals, audit_log, settings.

    NOT IMPLEMENTED — stub bodies raise NotImplementedError.
    Activate by setting STORAGE_BACKEND=cosmos and COSMOS_CONNECTION_STRING in .env.
    """

    def __init__(self, connection_string: str, database_name: str) -> None:
        self._connection_string = connection_string
        self._database_name = database_name
        self._client: Any = None
        self._db: Any = None

    async def initialize(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def _ensure_indexes(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Threads
    async def add_thread(self, thread: OperationalThread) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def get_thread(self, thread_id: str) -> OperationalThread | None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def list_threads(self, user_id: str | None = None) -> list[OperationalThread]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Incidents
    async def upsert_incident(self, record: IncidentRecord) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def get_incident(self, incident_id: str) -> IncidentRecord | None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def list_incidents(self, filters: dict | None = None) -> list[IncidentRecord]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Agent outputs
    async def add_output(self, output: AgentOutput) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def get_outputs(self, target_id: str | None = None) -> list[AgentOutput]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Approvals
    async def add_approval(self, task: ApprovalTask) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def update_approval(self, task_id: str, decision: ApprovalDecision) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def list_approvals(self, status: str | None = None) -> list[ApprovalTask]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Audit
    async def log_event(self, kind: str, payload: dict) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def get_audit_log(self, limit: int = 100) -> list[AuditEvent]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Settings
    async def get_settings(self) -> RuntimeSettings:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def save_settings(self, settings: RuntimeSettings) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    # Dashboard
    async def snapshot(self) -> DashboardSnapshot:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)
