from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.connectors import build_connectors
from app.middleware.logging import StructuredLoggingMiddleware
from app.routes import assistants, chat, dashboard, health, incidents, approvals, settings, threads
from app.services.orchestrator import Orchestrator
from app.store.factory import create_domain_store

# ---------------------------------------------------------------------------
# Logging configuration — structured JSON-style records via standard library
# ---------------------------------------------------------------------------

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","loc":"%(filename)s:%(lineno)d","message":"%(message)s"}',
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        # Suppress noisy library loggers
        "loggers": {
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "openai": {"level": "WARNING"},
            "azure": {"level": "WARNING"},
            "langgraph": {"level": "INFO"},
        },
    }
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Initialize all services at startup; release resources on shutdown.

    Startup order (required):
    1. ``Settings``          — load env vars
    2. ``create_domain_store``  — Tier 3 domain state
    3. ``build_connectors``     — external service clients
    4. ``Orchestrator.initialize()``  — LangGraph compile + Tier 1 checkpointer

    All four objects are attached to ``app.state`` and retrieved in route
    handlers via the dependency helpers in ``app.routes``.
    """
    # 1. Configuration
    _settings = Settings()
    logger.info(
        "Startup — storage=%s auth_disabled=%s",
        _settings.storage_backend,
        _settings.auth_disabled,
    )

    # 2. Domain store (Tier 3)
    store = await create_domain_store(_settings)
    logger.info("Domain store ready: %s", type(store).__name__)

    # 3. Connector bundle
    connectors = build_connectors(_settings, store)
    logger.info("Connectors built — live: %s", _connectors_live_summary(connectors))

    # 4. Orchestrator (compiles LangGraph + wires Tier 1 checkpointer)
    orchestrator = Orchestrator(_settings, connectors, store)
    await orchestrator.initialize()
    logger.info("Orchestrator ready")

    # Attach to app state — all route dependencies read from here
    app.state.settings = _settings
    app.state.store = store
    app.state.connectors = connectors
    app.state.orchestrator = orchestrator

    yield

    # Shutdown
    logger.info("Shutdown — cleaning up resources")


def _connectors_live_summary(bundle: Any) -> str:
    live = []
    for name in ("azure_openai", "azure_search", "servicenow", "teams"):
        connector = getattr(bundle, name, None)
        if connector and getattr(connector, "_live", False):
            live.append(name)
    return ", ".join(live) if live else "none (all using fallbacks)"


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Separated from module-level ``app`` to make testing easier:
    tests can call ``create_app()`` directly with overridden lifespan.
    """
    _app = FastAPI(
        title="AI Operations Concierge",
        description=(
            "Approval-first enterprise AI platform for IT Operations. "
            "Orchestrates AI agents to triage incidents, retrieve knowledge, "
            "draft RCAs, and manage ServiceNow records."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # -- CORS ----------------------------------------------------------------
    # Read allowed origins from Settings at import-time for the middleware;
    # a one-time Settings() is cheap and avoids a secondary app.state lookup.
    try:
        _cors_origins = Settings().cors_origins
    except Exception:
        _cors_origins = ["http://localhost:5173"]

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Structured request logging ------------------------------------------
    _app.add_middleware(StructuredLoggingMiddleware)

    # -- Routers -------------------------------------------------------------
    _app.include_router(health.router)
    _app.include_router(chat.router)
    _app.include_router(threads.router)
    _app.include_router(dashboard.router)
    _app.include_router(incidents.router)
    _app.include_router(approvals.router)
    _app.include_router(settings.router)
    _app.include_router(assistants.router)

    # -- Exception handlers --------------------------------------------------
    @_app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    @_app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": f"Not found: {exc}"},
        )

    @_app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    return _app


# ---------------------------------------------------------------------------
# Module-level app instance — used by uvicorn
# ---------------------------------------------------------------------------

app = create_app()
