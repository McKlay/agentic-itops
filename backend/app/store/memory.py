from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from app.models.agent import AgentOutput
from app.models.approval import ApprovalDecision, ApprovalTask
from app.models.chat import OperationalThread
from app.models.dashboard import DashboardSnapshot, MetricPayload
from app.models.domain import IncidentRecord, KnowledgeArticle
from app.store.base import AuditEvent, DomainStoreInterface, RuntimeSettings

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class InMemoryStore(DomainStoreInterface):
    """POC implementation — dict-backed, seeded with realistic demo data on startup.

    Thread-safe for single-process use (no async locks needed for dict ops in CPython).
    """

    def __init__(self) -> None:
        self._threads: dict[str, OperationalThread] = {}
        self._messages: dict[str, list] = defaultdict(list)       # thread_id → [MessageRecord]
        self._incidents: dict[str, IncidentRecord] = {}
        self._knowledge: dict[str, KnowledgeArticle] = {}
        self._outputs: list[AgentOutput] = []
        self._approvals: dict[str, ApprovalTask] = {}
        self._audit: list[AuditEvent] = []
        self._settings: RuntimeSettings = RuntimeSettings()

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    async def seed(self) -> None:
        """Populate with realistic demo data for local development & demos."""
        ts = _now()

        # --- Demo incidents ---
        incidents = [
            IncidentRecord(
                incident_id="INC0001001",
                sys_id="abc001",
                number="INC0001001",
                short_description="SAP login failures — P&G Global HR portal",
                description="Multiple users reporting inability to authenticate to the SAP HR portal "
                            "since 06:00 UTC. Affects approximately 120 users in EMEA region.",
                state="in_progress",
                priority="2",
                category="Application",
                assignment_group="SAP Operations",
                assigned_to="Jane Smith",
                opened_at=ts,
            ),
            IncidentRecord(
                incident_id="INC0001002",
                sys_id="abc002",
                number="INC0001002",
                short_description="Azure AD conditional access blocking MFA enrollment",
                description="New hire batch unable to complete MFA enrollment. "
                            "Conditional access policy is blocking the registration flow.",
                state="new",
                priority="2",
                category="Identity & Access",
                assignment_group="Identity Platform",
                opened_at=ts,
            ),
            IncidentRecord(
                incident_id="INC0001003",
                sys_id="abc003",
                number="INC0001003",
                short_description="Network latency spike — Cincinnati DC interconnect",
                description="Monitoring alerts show 800ms average latency on the Cincinnati–Columbus "
                            "data center MPLS link. Normal baseline is <10ms.",
                state="in_progress",
                priority="1",
                category="Network",
                assignment_group="Network Operations",
                assigned_to="Bob Lee",
                opened_at=ts,
            ),
        ]
        for inc in incidents:
            self._incidents[inc.incident_id] = inc

        # --- Demo knowledge articles ---
        articles = [
            KnowledgeArticle(
                article_id="ka_0001",
                sys_id="ka001",
                number="KB0001001",
                title="SAP Single Sign-On Troubleshooting Guide",
                text="Step-by-step guide for resolving SAP SSO failures including SAML assertion "
                     "errors, certificate expiry, and Active Directory trust issues. "
                     "Key steps: 1) Check IdP certificate on ADFS console. "
                     "2) Verify SP metadata in SAP SICF. "
                     "3) Review SAML trace in browser dev tools.",
                category="SAP",
                author="SAP Operations",
                published_at=ts,
                workflow_state="published",
                search_score=0.97,
            ),
            KnowledgeArticle(
                article_id="ka_0002",
                sys_id="ka002",
                number="KB0001002",
                title="Azure AD Conditional Access — MFA Registration Exemption Procedure",
                text="Procedure to temporarily exempt device groups from conditional access during "
                     "MFA enrollment windows. Requires Global Administrator or Conditional Access "
                     "Administrator role. Steps: Create named location for onboarding subnet, "
                     "add exclusion to policy, set 24-hour window, remove after enrollment.",
                category="Identity & Access",
                author="Identity Platform",
                published_at=ts,
                workflow_state="published",
                search_score=0.93,
            ),
            KnowledgeArticle(
                article_id="ka_0003",
                sys_id="ka003",
                number="KB0001003",
                title="MPLS Latency Runbook — DC Interconnect",
                text="Runbook for diagnosing high latency on P&G MPLS circuits. "
                     "Tools: SolarWinds NTA, Cisco IOSXE traceroute, NetScope. "
                     "Common causes: BGP route flap, QoS misconfiguration, physical layer errors. "
                     "Escalation path: NOC L1 → Network Ops L2 → Carrier TAC.",
                category="Network",
                author="Network Operations",
                published_at=ts,
                workflow_state="published",
                search_score=0.89,
            ),
        ]
        for ka in articles:
            self._knowledge[ka.article_id] = ka

        # --- Demo thread ---
        thread_id = "thr_demo_001"
        self._threads[thread_id] = OperationalThread(
            thread_id=thread_id,
            user_id="dev@local",
            title="Demo conversation",
            created_at=ts,
            updated_at=ts,
            message_count=0,
        )

        logger.info(
            "InMemoryStore seeded: %d incidents, %d articles, %d threads",
            len(self._incidents),
            len(self._knowledge),
            len(self._threads),
        )

    # ------------------------------------------------------------------
    # Threads
    # ------------------------------------------------------------------

    async def add_thread(self, thread: OperationalThread) -> None:
        self._threads[thread.thread_id] = thread
        await self.log_event("thread.created", {"thread_id": thread.thread_id})

    async def get_thread(self, thread_id: str) -> OperationalThread | None:
        return self._threads.get(thread_id)

    async def list_threads(self, user_id: str | None = None) -> list[OperationalThread]:
        threads = list(self._threads.values())
        if user_id:
            threads = [t for t in threads if t.user_id == user_id]
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def add_message(self, message: object) -> None:  # type: ignore[override]
        from app.models.chat import MessageRecord
        assert isinstance(message, MessageRecord)
        self._messages[message.thread_id].append(message)
        if message.thread_id in self._threads:
            t = self._threads[message.thread_id]
            self._threads[message.thread_id] = t.model_copy(
                update={"message_count": t.message_count + 1, "updated_at": _now()}
            )

    async def get_messages(self, thread_id: str) -> list:
        return list(self._messages.get(thread_id, []))

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------

    async def upsert_incident(self, record: IncidentRecord) -> None:
        self._incidents[record.incident_id] = record
        await self.log_event("incident.upserted", {"incident_id": record.incident_id})

    async def get_incident(self, incident_id: str) -> IncidentRecord | None:
        return self._incidents.get(incident_id)

    async def list_incidents(self, filters: dict | None = None) -> list[IncidentRecord]:
        records = list(self._incidents.values())
        if filters:
            if state := filters.get("state"):
                records = [r for r in records if r.state == state]
            if priority := filters.get("priority"):
                records = [r for r in records if r.priority == priority]
        return records

    # ------------------------------------------------------------------
    # Knowledge articles
    # ------------------------------------------------------------------

    async def upsert_knowledge(self, article: KnowledgeArticle) -> None:
        self._knowledge[article.article_id] = article

    async def get_knowledge(self, article_id: str) -> KnowledgeArticle | None:
        return self._knowledge.get(article_id)

    async def list_knowledge(self) -> list[KnowledgeArticle]:
        return list(self._knowledge.values())

    # ------------------------------------------------------------------
    # Agent outputs
    # ------------------------------------------------------------------

    async def add_output(self, output: AgentOutput) -> None:
        self._outputs.append(output)
        await self.log_event("output.added", {"output_id": output.output_id, "agent_id": output.agent_id})

    async def get_outputs(self, target_id: str | None = None) -> list[AgentOutput]:
        if target_id:
            return [o for o in self._outputs if o.target_id == target_id]
        return list(self._outputs)

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    async def add_approval(self, task: ApprovalTask) -> None:
        self._approvals[task.task_id] = task
        await self.log_event("approval.created", {"task_id": task.task_id})

    async def update_approval(self, task_id: str, decision: ApprovalDecision) -> None:
        if task_id not in self._approvals:
            raise KeyError(task_id)
        task = self._approvals[task_id]
        self._approvals[task_id] = task.model_copy(
            update={
                "status": decision.decision,
                "reviewed_by": decision.reviewer,
                "reviewer_comment": decision.comment,
                "reviewed_at": _now(),
            }
        )
        await self.log_event(
            "approval.updated",
            {"task_id": task_id, "decision": decision.decision, "reviewer": decision.reviewer},
        )

    async def list_approvals(self, status: str | None = None) -> list[ApprovalTask]:
        tasks = list(self._approvals.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    async def log_event(self, kind: str, payload: dict) -> None:  # type: ignore[override]
        event = AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            kind=kind,
            payload=payload,
            created_at=_now(),
        )
        self._audit.append(event)

    async def get_audit_log(self, limit: int = 100) -> list[AuditEvent]:
        return list(reversed(self._audit))[:limit]

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def get_settings(self) -> RuntimeSettings:
        return self._settings

    async def save_settings(self, settings: RuntimeSettings) -> None:
        self._settings = settings
        await self.log_event("settings.saved", {})

    # ------------------------------------------------------------------
    # Dashboard snapshot
    # ------------------------------------------------------------------

    async def snapshot(self) -> DashboardSnapshot:
        incidents = list(self._incidents.values())
        open_inc = [i for i in incidents if i.state not in ("resolved", "closed")]
        p1 = [i for i in open_inc if i.priority == "1"]
        p2 = [i for i in open_inc if i.priority == "2"]
        pending_approvals = [t for t in self._approvals.values() if t.status == "pending"]

        return DashboardSnapshot(
            snapshot_id=f"snap_{uuid.uuid4().hex[:8]}",
            generated_at=_now(),
            open_incidents=len(open_inc),
            p1_incidents=len(p1),
            p2_incidents=len(p2),
            mttr_hours=4.2,        # demo value
            sla_compliance_pct=94.7,
            open_problems=0,
            pending_changes=0,
            kb_articles=len(self._knowledge),
            kb_gap_count=0,
            total_threads=len(self._threads),
            pending_approvals=len(pending_approvals),
            agent_runs_today=0,
            metrics=[
                MetricPayload(name="Open Incidents", value=len(open_inc), unit="count", trend="stable"),
                MetricPayload(name="P1 Incidents", value=len(p1), unit="count", trend="stable"),
                MetricPayload(name="SLA Compliance", value=94.7, unit="%", trend="up"),
                MetricPayload(name="MTTR", value=4.2, unit="hrs", trend="down"),
            ],
        )
