from __future__ import annotations

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.dashboard import DashboardSnapshot
from app.routes import get_store
from app.services.dashboard import DashboardService
from app.store.base import DomainStoreInterface

router = APIRouter(tags=["Dashboard"])


@router.get("/api/dashboard", summary="Get operational metrics snapshot")
async def dashboard(
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> DashboardSnapshot:
    """Return a point-in-time aggregation of IT operations metrics."""
    service = DashboardService(store)
    return await service.snapshot()
