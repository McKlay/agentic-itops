from __future__ import annotations

"""Structured request/response logging middleware.

Logs each HTTP request as a single structured log record containing:
  - ``method``       — HTTP verb (GET, POST, …)
  - ``path``         — URL path (query string excluded)
  - ``status_code``  — response status
  - ``duration_ms``  — wall-clock time in milliseconds
  - ``user_id``      — extracted from X-User-Id header if set by auth layer
  - ``trace_id``     — value of X-Request-Id header (or auto-generated UUID)

Wire into the FastAPI app in ``app/main.py``::

    from app.middleware.logging import StructuredLoggingMiddleware
    app.add_middleware(StructuredLoggingMiddleware)

Note: ``BaseHTTPMiddleware`` wraps the ASGI call stack. For streaming responses
the ``duration_ms`` captures time-to-first-byte; body streaming continues after
this middleware returns.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("falcon.access")

# Paths excluded from access logging (e.g. liveness probes)
_SKIP_PATHS: frozenset[str] = frozenset({"/healthz", "/favicon.ico"})


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response as a structured JSON-compatible record.

    Fields emitted per request:
    - ``method``, ``path``, ``status_code``, ``duration_ms``
    - ``user_id`` — from ``X-User-Id`` header (populated by auth layer downstream)
    - ``trace_id`` — from ``X-Request-Id`` header; auto-generated UUID4 if absent
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # Generate or propagate trace ID
        trace_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex

        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        path = request.url.path

        if path not in _SKIP_PATHS:
            user_id = request.headers.get("X-User-Id", "")
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "trace_id": trace_id,
                },
            )

        # Propagate trace ID in response so clients can correlate
        response.headers["X-Request-Id"] = trace_id
        return response
