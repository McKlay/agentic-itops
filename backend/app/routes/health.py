from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Health"])

# Aligned with SVC §10.5 — unauthenticated, no Depends(get_current_user)


@router.get("/healthz", summary="Liveness + connector health check")
async def health(request: Request) -> dict:
    """Return application health and per-connector connectivity status.

    Does **not** require authentication — suitable for load-balancer probes.
    """
    connectors = request.app.state.connectors
    return {
        "status": "healthy",
        "version": "1.0.0",
        "connectors": {
            "azure_openai": (await connectors.azure_openai.health_check()).model_dump(),
            "azure_search": (await connectors.azure_search.health_check()).model_dump(),
            "servicenow": (await connectors.servicenow.health_check()).model_dump(),
            "teams": (await connectors.teams.health_check()).model_dump(),
        },
    }
