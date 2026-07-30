from __future__ import annotations

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.routes import get_store
from app.store.base import DomainStoreInterface, RuntimeSettings

router = APIRouter(tags=["Settings"])


@router.get("/api/settings", summary="Get runtime settings")
async def get_settings(
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> RuntimeSettings:
    """Return current runtime settings (persona, thresholds, feature flags)."""
    return await store.get_settings()


@router.put("/api/settings", summary="Update runtime settings")
async def update_settings(
    body: RuntimeSettings,
    store: DomainStoreInterface = Depends(get_store),
    user: CurrentUser = Depends(get_current_user),
) -> RuntimeSettings:
    """Persist updated runtime settings and return the saved state."""
    await store.save_settings(body)
    await store.log_event(
        "settings_updated",
        {"updated_by": user.email or user.user_id, "settings": body.model_dump()},
    )
    return await store.get_settings()
