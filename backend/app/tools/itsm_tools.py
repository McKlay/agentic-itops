from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.connectors.servicenow import ServiceNowConnector

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED = (
    "ITSM tool not fully wired — ServiceNow connector in fallback mode. "
    "Configure SNOW_INSTANCE_URL / SERVICENOW_USERNAME / SERVICENOW_PASSWORD to enable live mode."
)


def make_itsm_tools(snow: "ServiceNowConnector"):
    """Return (lookup_incident, create_incident, update_incident) closures bound to ``snow``."""

    async def lookup_incident(incident_id: str) -> dict[str, Any] | None:
        """Look up a ServiceNow incident by number or sys_id."""
        logger.debug("lookup_incident id=%r", incident_id)
        return await snow.get_incident(incident_id)

    async def create_incident(
        short_description: str,
        priority: str = "3",
        description: str = "",
        category: str = "",
        assignment_group: str = "",
    ) -> dict[str, Any]:
        """Create a new ServiceNow incident. Requires prior human approval."""
        logger.debug("create_incident short_description=%r", short_description)
        data: dict[str, Any] = {
            "short_description": short_description,
            "priority": priority,
        }
        if description:
            data["description"] = description
        if category:
            data["category"] = category
        if assignment_group:
            data["assignment_group"] = assignment_group
        return await snow.create_incident(data)

    async def update_incident(
        sys_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Update fields on an existing ServiceNow incident. Requires prior human approval."""
        logger.debug("update_incident sys_id=%r fields=%s", sys_id, list(fields.keys()))
        return await snow.update_incident(sys_id, fields)

    return lookup_incident, create_incident, update_incident
