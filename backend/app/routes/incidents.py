from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.domain import IncidentRecord
from app.routes import get_store
from app.store.base import DomainStoreInterface

router = APIRouter(tags=["Incidents"])


@router.get("/api/incidents", summary="List all incidents")
async def list_incidents(
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> list[IncidentRecord]:
    """Return all incidents from the domain store (seeded or live)."""
    return await store.list_incidents()


@router.get("/api/incidents/{incident_id}", summary="Get incident detail")
async def get_incident(
    incident_id: str,
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> IncidentRecord:
    """Return a single incident by ``incident_id``.

    ``incident_id`` may be a sys_id or incident number (e.g. ``INC0012345``).
    """
    record = await store.get_incident(incident_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id!r} not found",
        )
    return record
