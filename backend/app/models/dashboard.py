from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetricPayload(BaseModel):
    """Single metric data point for the dashboard."""

    name: str
    value: float
    unit: str = ""
    trend: str = "stable"                              # up | down | stable
    change_pct: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardSnapshot(BaseModel):
    """Cached aggregation of IT operations metrics returned by GET /api/dashboard."""

    snapshot_id: str = ""
    generated_at: str = ""

    # Incident KPIs
    open_incidents: int = 0
    p1_incidents: int = 0
    p2_incidents: int = 0
    mttr_hours: float = 0.0
    sla_compliance_pct: float = 0.0

    # Problem / Change
    open_problems: int = 0
    pending_changes: int = 0

    # Knowledge
    kb_articles: int = 0
    kb_gap_count: int = 0

    # Agent activity
    total_threads: int = 0
    pending_approvals: int = 0
    agent_runs_today: int = 0

    # Arbitrary metric tiles for the UI
    metrics: list[MetricPayload] = Field(default_factory=list)
