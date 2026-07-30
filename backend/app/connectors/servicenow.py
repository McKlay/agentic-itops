from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import Settings
from app.connectors.base import ConnectorBase, ConnectorHealth

_SNOW_FIELDS = (
    "sys_id,number,short_description,description,state,priority,"
    "category,assigned_to,assignment_group,caller_id,opened_at,resolved_at,close_notes"
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ServiceNowConnector(ConnectorBase):
    """ServiceNow REST API connector (Table API).

    Tables used: ``incident``, ``kb_knowledge``, ``problem``, ``change_request``
    Auth: HTTP Basic (service account — SERVICENOW_USERNAME / SERVICENOW_PASSWORD)

    POC fallback: operates against an in-memory dict seeded from the Domain Store.
    Approval-first: ``create_incident`` and ``update_incident`` should only be
    called after an ``ApprovalTask`` has been approved by a human reviewer.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._base_url = (settings.snow_instance_url or "").rstrip("/")
        self._username = settings.servicenow_username
        self._password = settings.servicenow_password
        self._fallback_incidents: dict[str, dict] = {}

        if self._base_url and self._username and self._password:
            self._live = True
            self.logger.info(
                "ServiceNowConnector live — instance=%s", self._base_url
            )
        else:
            self.logger.warning(
                "ServiceNowConnector offline — SNOW_INSTANCE_URL / "
                "SERVICENOW_USERNAME / SERVICENOW_PASSWORD not set. Using fallback."
            )

    # ------------------------------------------------------------------
    # Incident operations
    # ------------------------------------------------------------------

    async def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        if not self._require_live("get_incident"):
            return self._fallback_incidents.get(incident_id)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/now/table/incident",
                params={
                    "sysparm_query": f"number={incident_id}",
                    "sysparm_fields": _SNOW_FIELDS,
                    "sysparm_limit": "1",
                },
                auth=(self._username, self._password),
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("result", [])
            return results[0] if results else None

    async def create_incident(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new incident. **Requires prior human approval.**"""
        if not self._require_live("create_incident"):
            return self._create_fallback(data)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/now/table/incident",
                json=data,
                auth=(self._username, self._password),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["result"]

    async def update_incident(self, sys_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Patch an existing incident by ``sys_id``. **Requires prior human approval.**"""
        if not self._require_live("update_incident"):
            stored = self._fallback_incidents.get(sys_id, {})
            stored.update(data)
            return stored

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self._base_url}/api/now/table/incident/{sys_id}",
                json=data,
                auth=(self._username, self._password),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["result"]

    # ------------------------------------------------------------------
    # Fallback helpers
    # ------------------------------------------------------------------

    def _create_fallback(self, data: dict[str, Any]) -> dict[str, Any]:
        fake_id = f"INC{uuid.uuid4().int % 10_000_000:07d}"
        record = {
            "number": fake_id,
            "sys_id": uuid.uuid4().hex,
            "state": "new",
            "opened_at": _now(),
            **data,
        }
        self._fallback_incidents[fake_id] = record
        self.logger.info("ServiceNow fallback: created incident %s", fake_id)
        return record

    def incident_url(self, sys_id: str) -> str:
        """Return the direct ServiceNow browser link for an incident."""
        return f"{self._base_url}/nav_to.do?uri=incident.do?sys_id={sys_id}" if self._base_url else ""

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> ConnectorHealth:
        if not self._live:
            return ConnectorHealth(
                name="servicenow",
                connected=False,
                source="fallback",
                error="Not configured",
            )
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/api/now/table/incident",
                    params={"sysparm_limit": "1", "sysparm_fields": "sys_id"},
                    auth=(self._username, self._password),
                    timeout=5,
                )
                resp.raise_for_status()
            latency = int((time.perf_counter() - start) * 1000)
            return ConnectorHealth(
                name="servicenow", connected=True, source="live", latency_ms=latency
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectorHealth(
                name="servicenow",
                connected=False,
                source="fallback",
                error=str(exc),
            )
