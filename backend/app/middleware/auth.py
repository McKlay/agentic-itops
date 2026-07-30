from __future__ import annotations

"""Entra ID JWT authentication dependency for FastAPI.

Usage in route handlers::

    from app.middleware.auth import get_current_user

    @router.get("/api/example")
    async def example(user: CurrentUser = Depends(get_current_user)):
        ...

Development bypass::

    AUTH_DISABLED=true  →  returns a synthetic "Developer" user; never used in production.
"""

import logging
from typing import Any

import httpx
from fastapi import HTTPException, Request, status
from jose import ExpiredSignatureError, JWTError, jwt
from jose.exceptions import JWKError

from app.models.auth import CurrentUser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS cache — fetched once per process, refreshed on key mismatch
# ---------------------------------------------------------------------------
_JWKS_CACHE: dict[str, Any] = {}


async def _fetch_jwks(tenant_id: str) -> dict[str, Any]:
    """Fetch and cache the Entra ID JWKS for the given tenant."""
    global _JWKS_CACHE  # noqa: PLW0603
    if _JWKS_CACHE:
        return _JWKS_CACHE

    url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _JWKS_CACHE = resp.json()
        logger.debug("JWKS refreshed from %s", url)
        return _JWKS_CACHE


def _extract_bearer_token(request: Request) -> str:
    """Pull the Bearer token from the Authorization header.

    Raises:
        HTTPException 401 if the header is missing or malformed.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header[len("Bearer "):]


async def _validate_jwt(token: str, settings: Any) -> dict[str, Any]:
    """Validate an Entra ID JWT and return its claims.

    Validation steps:
    1. Decode header to get ``kid``
    2. Find matching key in JWKS
    3. Decode and verify signature, ``aud``, ``iss``, ``exp``

    Args:
        token: Raw JWT string (without "Bearer " prefix).
        settings: ``app.config.Settings`` instance.

    Returns:
        Decoded JWT claims dict.

    Raises:
        HTTPException 401 on any validation failure.
    """
    tenant_id: str = settings.entra_tenant_id
    client_id: str = settings.entra_client_id

    if not tenant_id or not client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication not configured on this server",
        )

    try:
        jwks = await _fetch_jwks(tenant_id)
    except Exception as exc:
        logger.error("Failed to fetch JWKS: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach authentication service",
        ) from exc

    # Decode without verification first to extract the key ID
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    kid = unverified_header.get("kid")
    signing_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            signing_key = key
            break

    if signing_key is None:
        # Force refresh and retry once on key mismatch
        global _JWKS_CACHE  # noqa: PLW0603
        _JWKS_CACHE = {}
        try:
            jwks = await _fetch_jwks(tenant_id)
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = key
                    break
        except Exception:
            pass

    if signing_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signing key not found",
        )

    expected_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=expected_issuer,
            options={"verify_exp": True},
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except (JWTError, JWKError) as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
        ) from exc

    return claims


# ---------------------------------------------------------------------------
# Public FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency — validate Entra ID JWT and return ``CurrentUser``.

    Attach via ``Depends(get_current_user)`` on any protected route.
    Set ``AUTH_DISABLED=true`` in ``.env`` to bypass JWT validation in local dev.

    Raises:
        HTTPException 401 for missing, expired, or invalid tokens.
        HTTPException 503 if the JWKS endpoint is unreachable.
    """
    settings = request.app.state.settings

    # Dev bypass — never enabled in production
    if getattr(settings, "auth_disabled", False):
        logger.debug("AUTH_DISABLED=true — returning synthetic dev user")
        return CurrentUser(
            user_id="dev",
            email="dev@local",
            name="Developer",
            roles=["admin"],
        )

    token = _extract_bearer_token(request)
    claims = await _validate_jwt(token, settings)

    return CurrentUser(
        user_id=claims.get("oid") or claims.get("sub", "unknown"),
        email=claims.get("preferred_username", ""),
        name=claims.get("name", ""),
        roles=claims.get("roles", []),
    )
