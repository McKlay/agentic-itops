from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stub telemetry tools — not wired to a live telemetry backend in POC.
# Production: connect to Azure Monitor / Application Insights via REST or SDK.
# ---------------------------------------------------------------------------

_STUB_SIGNALS: list[dict[str, Any]] = [
    {
        "alert_id": "ALT001",
        "severity": "Sev1",
        "resource": "sap-hr-portal",
        "description": "Response time > 5s threshold breached",
        "fired_at": "2026-05-04T06:05:00Z",
        "state": "fired",
    },
    {
        "alert_id": "ALT002",
        "severity": "Sev2",
        "resource": "cincinnati-dc-interconnect",
        "description": "Network latency > 500ms (baseline: <10ms)",
        "fired_at": "2026-05-04T07:12:00Z",
        "state": "fired",
    },
]

_STUB_METRICS: dict[str, dict[str, float]] = {
    "cpu_percent": {"avg": 72.4, "max": 91.0, "min": 48.2},
    "latency_ms": {"avg": 820.0, "max": 1430.0, "min": 210.0},
    "error_rate": {"avg": 4.2, "max": 11.0, "min": 0.0},
    "memory_percent": {"avg": 65.1, "max": 78.3, "min": 55.0},
}


async def get_signals(resource: str, minutes: int = 60) -> list[dict[str, Any]]:
    """Return active monitoring alerts for *resource* over the last *minutes*.

    POC: returns stub signals filtered by resource substring match.
    Production: query Azure Monitor Alerts REST API or Application Insights.
    """
    logger.debug("get_signals resource=%r minutes=%d (stub)", resource, minutes)
    r = resource.lower()
    filtered = [s for s in _STUB_SIGNALS if r in s["resource"].lower()]
    return filtered or _STUB_SIGNALS[:1]


async def get_metrics(
    resource: str,
    metric_names: list[str],
    minutes: int = 60,
) -> dict[str, Any]:
    """Return performance metrics for *resource* over the last *minutes*.

    POC: returns stub metric aggregates regardless of resource.
    Production: query Azure Monitor Metrics REST API.
    """
    logger.debug(
        "get_metrics resource=%r metrics=%s minutes=%d (stub)",
        resource,
        metric_names,
        minutes,
    )
    return {
        "resource": resource,
        "window_minutes": minutes,
        "sampled_at": datetime.now(UTC).isoformat(),
        "metrics": {
            name: _STUB_METRICS.get(name, {"avg": 0.0, "max": 0.0, "min": 0.0})
            for name in metric_names
        },
    }
