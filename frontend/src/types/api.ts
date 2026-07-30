/* ── View Types ──────────────────────────────────────── */

export type ViewType =
  | 'home'
  | 'conversation'
  | 'incidents'
  | 'problems'
  | 'changes'
  | 'observability'
  | 'performance';

/* ── Domain Records ─────────────────────────────────── */

export interface IncidentRecord {
  id: string;
  title: string;
  service: string;
  domain: string;
  severity: 1 | 2 | 3 | 4;
  status: string;
  summary: string;
  assignee: string;
  opened_at: string;
  accepted_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  telemetry_tags: string[];
}

export interface ProblemRecord {
  id: string;
  title: string;
  service: string;
  domain: string;
  status: string;
  linked_incidents: string[];
  summary: string;
  corrective_actions: string[];
  created_at: string;
}

export interface ChangeRecord {
  id: string;
  title: string;
  service: string;
  domain: string;
  status: string;
  rationale: string;
  implementation_plan: string[];
  approvals: string[];
  created_at: string;
}

export interface KnowledgeArticle {
  id: string;
  title: string;
  source: string;
  summary: string;
  services: string[];
  tags: string[];
  validated: boolean;
}

export interface TelemetrySignal {
  id: string;
  service: string;
  category: 'metric' | 'log' | 'alert';
  summary: string;
  severity: string;
  tags: string[];
  observed_at: string;
}

/* ── Agent Models ───────────────────────────────────── */

/** Mirrors ``app/models/agent.py :: AgentOutput`` */
export interface AgentOutput {
  output_id: string;
  agent_id: string;
  intent: string;
  summary: string;
  detail: string;
  steps: string[];           // numbered procedure steps (procedural answers only)
  notes: string[];           // key caveats / warnings
  citations: string[];
  citation_urls: Record<string, string>; // citation string → blob PDF URL
  requires_approval: boolean;
  status: 'pending' | 'approved' | 'rejected';
  confidence: number;
  created_at: string;
  target_id: string | null;
}

/** Mirrors ``app/models/approval.py :: ApprovalTask`` */
export interface ApprovalTask {
  task_id: string;
  output_id: string;
  thread_id: string;
  agent_id: string;
  summary: string;
  status?: string;
  created_at: string;
}

/* ── Chat Models ────────────────────────────────────── */

export interface Session {
  id: string;
  title: string;
  meta: string;
  kind: string;
}

export type RatingLevel = 'poor' | 'fair' | 'good' | 'great' | 'excellent';

export interface Artifact {
  type: string;
  data: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  kind?: string;
  artifacts?: Artifact[];
  rating?: RatingLevel;
  created_at: string;
}

/* ── Chat API ───────────────────────────────────────── */

/** Mirrors ``app/models/chat.py :: ChatRequest`` */
export interface ChatRequest {
  message: string;
  thread_id?: string;   // omit to let backend auto-create
}

/** Mirrors ``app/models/chat.py :: ChatResponse`` */
export interface ChatResponse {
  thread_id: string;
  message: string;
  agent_outputs: AgentOutput[];
  pending_approvals: ApprovalTask[];
  timestamp: string;
}

/* ── Dashboard ──────────────────────────────────────── */

export interface AuditEvent {
  kind: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface DashboardSnapshot {
  incidents: IncidentRecord[];
  problems: ProblemRecord[];
  changes: ChangeRecord[];
  knowledge_articles: KnowledgeArticle[];
  telemetry_signals: TelemetrySignal[];
  outputs: AgentOutput[];
  approvals: ApprovalTask[];
  agents: Record<string, unknown>[];
  metrics: Record<string, unknown>;
  audit_log: AuditEvent[];
}

/* ── Incidents Overview ─────────────────────────────── */

export interface IncidentFilters {
  search: string;
  status: string;
  priority: string;
  timeWindow: string;
  page: number;
  pageSize: number;
}

export interface SlaSummary {
  response_compliance: number;
  resolution_compliance: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ConnectorHealth {
  connected: boolean;
  source: string;
  latency_ms: number | null;
  error: string | null;
}

export interface IncidentsOverview {
  incidents: IncidentRecord[];
  sla_summary: SlaSummary;
  live_status: ConnectorHealth;
  pagination: PaginationMeta;
}

/* ── Settings ───────────────────────────────────────── */

export interface NamingSettings {
  brand_name: string;
  assistant_name: string;
  command_center_title: string;
  platform_title: string;
  sidebar_subtitle: string;
}

export interface ServiceNowConfig {
  enabled: boolean;
  base_url: string;
  default_domain: string;
  username: string;
  password: string;
  incident_page_limit: number;
  verify_ssl: boolean;
}

export interface SharePointConfig {
  enabled: boolean;
  site_id: string;
  drive_id: string;
  repository: string;
}

export interface OutlookConfig {
  enabled: boolean;
  sender: string;
  recipients: string;
}

export interface TeamsConfig {
  enabled: boolean;
  team_id: string;
  channel_id: string;
  approval_mode: string;
}

export interface ConnectorSettings {
  servicenow: ServiceNowConfig;
  sharepoint: SharePointConfig;
  outlook: OutlookConfig;
  teams: TeamsConfig;
}

export interface GeneralInstructions {
  platform: string;
  response_style: string;
  approval_policy: string;
}

export interface SlaTargets {
  [priority: string]: {
    response_minutes: number;
    resolution_hours: number;
  };
}

export interface KpiTargets {
  mttr_target_hours: number;
  first_contact_resolution_pct: number;
  change_success_rate_pct: number;
  knowledge_reuse_pct: number;
  approval_sla_minutes: number;
  csat_target_pct: number;
}

export interface RuntimeSettings {
  naming: NamingSettings;
  connectors: ConnectorSettings;
  user_personas: Record<string, string>;
  agent_personas: Record<string, string>;
  general_instructions: GeneralInstructions;
  metrics: {
    sla: SlaTargets;
    kpis: KpiTargets;
  };
}

export interface ConnectorTestResult {
  status: 'success' | 'warning' | 'error' | 'pending';
  message: string;
}

/* ── Auth ────────────────────────────────────────────── */

export interface AuthUser {
  name: string;
  email: string;
  roles: string[];
}

/* ── Feed Card ──────────────────────────────────────── */

export type FeedType = 'monitoring' | 'incident' | 'problem' | 'orchestration';
