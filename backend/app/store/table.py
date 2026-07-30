from __future__ import annotations

import logging
from typing import Any

from app.models.agent import AgentOutput
from app.models.approval import ApprovalDecision, ApprovalTask
from app.models.chat import OperationalThread
from app.models.dashboard import DashboardSnapshot
from app.models.domain import IncidentRecord
from app.store.base import AuditEvent, DomainStoreInterface, RuntimeSettings, TableStoreBase

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED_MSG = (
    "TableStore is not yet implemented. "
    "Provision an Azure Storage account and set AZURE_TABLE_CONNECTION_STRING in .env."
)


class TableStore(TableStoreBase, DomainStoreInterface):
    """Alternative store — Azure Table Storage.

    Cost-optimised for simpler query patterns (key-value lookups, no aggregations).
    Uses azure-data-tables SDK.

    NOT IMPLEMENTED — stub bodies raise NotImplementedError.
    Activate by setting STORAGE_BACKEND=azure_table and AZURE_TABLE_CONNECTION_STRING in .env.
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._client: Any = None

    async def initialize(self) -> None:
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
