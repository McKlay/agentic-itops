# Frontend Component Reference

> **Companion to:** [FRONTEND-ARCHITECTURE.md](FRONTEND-ARCHITECTURE.md)  
> **Source UI:** KnowledgeForge2 `command_center.html` (5,260 lines, single-file Jinja2 template)  
> **Target:** React 19 + Tailwind CSS 4 component decomposition

This document specifies every component needed to recreate the KnowledgeForge2 Command Center UI as a React application.

---

## 1. Layout Components

### `AppShell.tsx`

**Location:** `src/components/layout/AppShell.tsx`

Three-panel CSS Grid container. Full viewport height, no overflow on body.

```
┌─────────────────────────────────────────────────────────┐
│ Sidebar (260px) │ Workspace (1fr)   │ ActivityFeed (320px)│
│                 │                   │                    │
└─────────────────────────────────────────────────────────┘
```

| Prop | Type | Description |
|---|---|---|
| — | — | No props — children are hardcoded layout slots |

**Tailwind classes:**
```
grid grid-cols-[260px_1fr_320px] h-screen overflow-hidden
bg-[var(--page)] text-[var(--text)] font-[Segoe_UI,Aptos,system-ui,sans-serif]
```

**Responsive behavior:**
- `max-w-[1180px]`: hide ActivityFeed, sidebar shrinks to 220px
- `max-w-[860px]`: hide Sidebar, single-column

---

### `Sidebar.tsx`

**Location:** `src/components/layout/Sidebar.tsx`

Fixed-width left rail with 5 sections stacked vertically.

#### Section 1 — Brand Block
- Logo image (24×24 or `/static/swiftassist-mark.png`)
- Brand title (`brand_name` from settings)
- Subtitle: "Agentic IT Operations"

#### Section 2 — Navigation Group (6 items)

| # | Label | Icon | View |
|---|---|---|---|
| 1 | `{brand_name} Hub` | `⌘` | `home` |
| 2 | Incidents | `◌` | `incidents` |
| 3 | Problems | `◌` | `problems` |
| 4 | Changes | `⇄` | `changes` |
| 5 | Observability | `◫` | `observability` |
| 6 | Agent Performance | `⚙` | `performance` |

Active item: `bg-[var(--surface-soft)]`, `color: var(--purple)`, `font-weight: 600`.

#### Section 3 — Chat Sessions
- Header: "Chat Sessions" + "+" add button
- Scrollable list of `SessionItem` entries
- Each session: title (editable on rename), meta text, hover reveals rename/delete icons
- Active session: `background: var(--surface-soft)`

#### Section 4 — Footer Controls
- **Role switch**: Chip showing current role → dropdown with 7 roles:
  - Support, Process Owner, Application Owner, Incident Manager, Problem Manager, Knowledge Manager, Client Delivery Manager
- **Support panel**: "Open incidents" / "Pending approvals" quick-action buttons
- **Theme switcher**: Light/Dark toggle chips
- **Profile trigger**: Avatar (initials circle) + name → dropdown menu with Profile, Personalization, Settings, Help, Log out

#### Section 5 — Footer Text
- "Powered by Azure OpenAI"

---

### `ActivityFeed.tsx`

**Location:** `src/components/layout/ActivityFeed.tsx`

Right rail with two sections:

#### Live Agent Feed
- Header: "Live Agent Feed"
- Scrollable list of `FeedCard` components
- Cards color-coded by type:
  - `monitoring`: `bg-[var(--yellow-soft)]`
  - `incident`: `bg-[var(--red-soft)]`
  - `problem`: `bg-[var(--surface)]`
  - `orchestration`: `bg-[var(--purple-soft)]`
- Each card: meta line (agent name + time) + description text + arrow icon

#### Metric Strip
- 3 `MetricTile` components at bottom:
  - **Open Incidents** (count)
  - **Pending Approvals** (count)
  - **MTTR Improvement** (percentage)

---

## 2. Page Components

### `HomePage.tsx`

**View state:** `home`

| Section | Content |
|---|---|
| Hero | Circular brand orb logo, greeting headline (`"How can I help you today?"`), subtitle |
| Quick Actions | 4 action cards in a 2×2 grid |

#### Quick Action Cards

| # | Label | Color | Action |
|---|---|---|---|
| 1 | "What incidents were opened this week?" | `bg-[var(--blue-soft)]` | Navigate to incidents with `timeWindow: 'this_week'` |
| 2 | "What problems are due this week?" | `bg-[var(--pink-soft)]` | Navigate to problems with `dueWindow: 'this_week'` |
| 3 | "Generate an RCA/CAP report for the top problem" | `bg-[var(--lavender-soft)]` | Trigger RCA report generation |
| 4 | "Search the knowledge base for troubleshooting steps" | `bg-[var(--mint-soft)]` | Submit chat message for KB search |

Each card: `rounded-2xl`, `padding: 20px 18px`, `cursor: pointer`, `font-weight: 600`, icon prefix.

---

### `IncidentsPage.tsx`

**View state:** `incidents`  
**Data source:** `GET /api/incidents/overview`

| Section | Component(s) |
|---|---|
| Header | Page title, live status pill, refresh button |
| Toolbar | `SearchInput` + `FilterChip`×3 (status, priority, time window) |
| Charts (2-column grid) | `BarChart` (incidents by priority), `DonutChart` (status breakdown) |
| SLA Summary | `SlaGauge`×2 (response time, resolution time) |
| Incident Table | `<table>` with columns: ID, Title, Service, Priority, Status, Assignee, Opened |
| Pagination | `PaginationControls` |

#### Filters

| Filter | Options | Default |
|---|---|---|
| Status | All, Open, In Progress, Resolved, Closed | All |
| Priority | All, P1, P2, P3, P4 | All |
| Time Window | All, This Week, This Month, Last 30 Days | All |

#### Live Status Pill
- Green dot + "Connected" when SNOW is reachable
- Yellow dot + "Slow" when latency > threshold
- Red dot + "Disconnected" when offline

---

### `ProblemsPage.tsx`

**View state:** `problems`  
**Data source:** `GET /api/dashboard`

| Section | Content |
|---|---|
| Header | Page title, filter chips (due window) |
| Problem Cards | Card per problem with: title, status pill, linked incidents count, RCA/CAP due dates |
| SLA Boxes | Per-problem: RCA Due date, CAP Due date with color-coded urgency |
| Actions | "Generate RCA Report" button per problem |

---

### `ChangesPage.tsx`

**View state:** `changes`  
**Data source:** `GET /api/dashboard`

| Section | Content |
|---|---|
| Header | Page title |
| Change Table | ID, Title, Service, Status, Rationale (truncated), Created |
| Timeline | 4-stage horizontal timeline per change: Draft → Review → Approved → Implemented |

Timeline stage styling: each stage is a rounded pill, filled stages have `bg-[var(--purple)]` + white text.

---

### `ObservabilityPage.tsx`

**View state:** `observability`  
**Data source:** `GET /api/dashboard`

| Section | Content |
|---|---|
| Header | Page title |
| Service Health Grid | Cards grouped by domain (Manufacturing, Planning, Warehousing) |
| Node Cards | Per service: health percentage bar, incident count, status color |

Node health bar: `bg-[var(--green)]` fill on track, red text for degraded services.

---

### `PerformancePage.tsx`

**View state:** `performance`  
**Data source:** `GET /api/dashboard?refresh=true`

| Section | Content |
|---|---|
| KPI Cards | 8 cards in 4×2 grid |
| Agent Matrix | Table: Agent name + 4-5 metrics with progress bars |

#### KPI Cards

| KPI | Unit |
|---|---|
| Mean Time to Resolve | hours |
| First Contact Resolution | percentage |
| Change Success Rate | percentage |
| Knowledge Reuse Rate | percentage |
| Approval SLA Compliance | percentage |
| Customer Satisfaction | score /5 |
| Adoption Rate | percentage |
| Hours Saved | hours/month |

Agent matrix progress bars: CSS `--fill` variable sets width, colored by threshold (green ≥ 80%, yellow ≥ 60%, red < 60%).

---

## 3. Chat Components

### `Conversation.tsx`

Scrollable container rendering a list of `MessageBubble` components. Auto-scrolls to bottom on new messages.

```tsx
<div className="flex-1 overflow-y-auto p-6">
  <div className="max-w-[760px] mx-auto space-y-4">
    {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
  </div>
</div>
```

---

### `MessageBubble.tsx`

| Prop | Type | Description |
|---|---|---|
| `message` | `Message` | Message record with role, content, metadata |

#### User Bubble
- Aligned right (`items-end`)
- Background: `#dbeafe` (light) / dark blue (dark)
- Avatar: initials circle (right side)
- `border-top-right-radius: 8px` (other corners: 20px)

#### Assistant Bubble
- Aligned left
- Background: `var(--surface)` with `1px` border
- Avatar: brand logo circle (left side)
- Agent name label above bubble
- `border-top-left-radius: 8px` (other corners: 20px)
- Meta line: `"{AssistantName} • {time}"` in `var(--muted)` text
- If rated: rating note below the bubble

#### Loading State
- Assistant bubble with spinner animation + "Thinking..." text
- Cancel button to abort

#### Artifact Message
- Replaces plain bubble with `ArtifactCard` component

---

### `Composer.tsx`

Bottom bar with input and controls.

| Element | Description |
|---|---|
| New conversation button | Creates new session, clears conversation |
| Clear button | Clears current conversation |
| Text input | `placeholder="Ask a question..."`, submit on Enter |
| Send button | Purple background, disabled when empty |
| Experience rating row | 5 emoji buttons below the input |

```
┌──────────────────────────────────────────────────────────┐
│ [+] [🗑] [Ask a question...                        ] [→] │
│           ☹  ◔  ◕  ☺  ★  Rate your experience          │
└──────────────────────────────────────────────────────────┘
```

---

### `ArtifactCard.tsx`

Rich structured card rendered inside assistant messages. Type determined by `kind` field.

#### Artifact Types

**RCA/CAP Report** (`kind: "report"`)

| Section | Content |
|---|---|
| Header | Title (green `#12814b`), subtitle with confidence % + "Human approval required" |
| Executive Summary | Paragraph |
| Root Cause Analysis | Paragraph |
| Corrective Action Plan | Bullet list |
| Supporting Evidence | Bullet list |
| Governance | Approval status text |

**Incident Detail** (`kind: "incident"`)

| Section | Content |
|---|---|
| Header | "Incident {ID}", subtitle message |
| Detail grid | Status, Priority, Owner, Created, Service |
| Description | Summary card |
| Actions | "Troubleshoot in KB", "Create KB Draft" buttons |
| Related KB | Up to 3 article title pills |

**Incident Resolution** (`kind: "incident_resolution"`)

| Section | Content |
|---|---|
| Header | "Resolution Recommendation {ID}" |
| Detail grid | Status, Priority, Owner, Service, Confidence % |
| Likely Cause | Paragraph |
| Next Steps | Bullet list |
| Evidence | Bullet list |
| Related | Article/ticket cards |

**Knowledge Draft** (`kind: "knowledge_draft"`)

| Section | Content |
|---|---|
| Header | Article title, "Local knowledge draft • Human validation required" |
| Message | Summary paragraph |
| Detail grid | Local Folder, Article Number, State, Approval Queue |
| Actions | Approve / Reject buttons (if pending) |
| Article body | Rendered HTML content (sanitized) |

---

### `ExperienceRating.tsx`

5-level rating bar attached to assistant messages.

| Level | Icon | Label |
|---|---|---|
| `poor` | ☹ | Poor |
| `fair` | ◔ | Fair |
| `good` | ◕ | Good |
| `great` | ☺ | Great |
| `excellent` | ★ | Excellent |

Active button: `bg-[var(--surface-tint)]`, `border-color: var(--line-strong)`, `color: var(--purple)`, `transform: translateY(-1px)`.

Ratings persisted to `localStorage` per message ID.

---

## 4. Shared Components

### `StatusPill.tsx`

| Prop | Type |
|---|---|
| `status` | `string` |
| `variant` | `'status' \| 'impact'` |

Color mapping:
- `low` / `resolved`: green bg/text
- `moderate` / `open`: blue bg/text
- `approved` / `implemented`: purple bg/text
- `incident` (impact): red bg/text
- `clean` (impact): green bg/text

```tsx
<span className="inline-block px-3 py-1 rounded-full text-xs font-medium ...">
  {status}
</span>
```

### `MetricTile.tsx`

| Prop | Type |
|---|---|
| `label` | `string` |
| `value` | `string \| number` |

Stacked layout: value (large, bold) above label (small, muted).
Background: `var(--surface)`, border: `var(--line)`, rounded-xl.

### `FeedCard.tsx`

| Prop | Type |
|---|---|
| `type` | `'monitoring' \| 'incident' \| 'problem' \| 'orchestration'` |
| `agent` | `string` |
| `time` | `string` |
| `description` | `string` |

Background mapped by type to `--yellow-soft`, `--red-soft`, `--surface`, `--purple-soft`.

### `BarChart.tsx`

CSS div-based bar chart. No charting library.

| Prop | Type |
|---|---|
| `data` | `{ label: string; value: number; color?: string }[]` |
| `title` | `string` |

Each bar: `div` with dynamic height proportional to max value. Labels below bars.

### `DonutChart.tsx`

CSS `conic-gradient` donut chart.

| Prop | Type |
|---|---|
| `segments` | `{ label: string; value: number; color: string }[]` |
| `title` | `string` |

Rendered as a `div` with:
```css
background: conic-gradient(/* segments */);
border-radius: 50%;
/* center hole via ::after pseudo-element */
```

Legend row below with color dots.

### `SlaGauge.tsx`

Horizontal track/fill progress bar.

| Prop | Type |
|---|---|
| `label` | `string` |
| `value` | `number` (0-100) |
| `target` | `number` |

Fill color: green (`≥ target`), yellow (`≥ target × 0.8`), red (`< target × 0.8`).

### `FilterChip.tsx`

Cycle-through filter button.

| Prop | Type |
|---|---|
| `label` | `string` |
| `options` | `string[]` |
| `value` | `string` |
| `onChange` | `(value: string) => void` |

Active state: `bg-[var(--purple)]`, white text.

### `SearchInput.tsx`

Debounced text input (250ms delay).

| Prop | Type |
|---|---|
| `placeholder` | `string` |
| `onSearch` | `(query: string) => void` |

### `PaginationControls.tsx`

| Prop | Type |
|---|---|
| `page` | `number` |
| `totalPages` | `number` |
| `onPageChange` | `(page: number) => void` |

Previous/Next buttons, disabled at boundaries.

---

## 5. Modal Components

### `SettingsModal.tsx`

Full-screen overlay (`position: fixed`, `inset: 0`, `z-index: 1000`).

**5 Tab Panels:**

| Tab | Panel Content |
|---|---|
| **Naming & Brand** | Brand name, command center title, platform title, sidebar subtitle inputs |
| **User Persona** | 7 textarea fields (one per role) for persona prompts |
| **Agent Persona & Instructions** | 6 agent textareas + 3 general instruction fields (platform, response style, approval policy) |
| **Connectors** | 4 connector cards in 2-column grid |
| **Metrics & SLA** | SLA targets (P1-P4 response/resolution) + KPI target inputs |

#### Connector Cards

| Connector | Fields |
|---|---|
| **ServiceNow** | Enable toggle, URL, domain, username, password, incident limit, SSL verify, test button |
| **SharePoint** | Graph tenant/client/secret, site ID, drive ID, repository, test button |
| **Outlook** | Enable toggle, sender, recipients, test button |
| **Teams** | Enable toggle, team ID, channel ID, approval mode dropdown, test button |

Test button shows status: success (green), warning (yellow), error (red), pending (gray).

Footer: Save button + Cancel button + status message.

### `ProfileModal.tsx`

Compact overlay showing: avatar circle with initials, name, email, current role, session status. Read-only.

### `HelpModal.tsx`

Static text overlay describing platform capabilities and the approval-first design.

---

## 6. TypeScript Interfaces (`src/types/api.ts`)

```typescript
// View types
type ViewType = 'home' | 'conversation' | 'incidents' | 'problems'
  | 'changes' | 'observability' | 'performance';

// Domain records (mirror Pydantic models)
interface IncidentRecord {
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

interface ProblemRecord {
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

interface ChangeRecord {
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

interface KnowledgeArticle {
  id: string;
  title: string;
  source: string;
  summary: string;
  services: string[];
  tags: string[];
  validated: boolean;
}

interface TelemetrySignal {
  id: string;
  service: string;
  category: 'metric' | 'log' | 'alert';
  summary: string;
  severity: string;
  tags: string[];
  observed_at: string;
}

// Agent models
interface AgentOutput {
  id: string;
  agent_id: string;
  target_type: 'incident' | 'problem' | 'change' | 'platform';
  target_id: string;
  title: string;
  summary: string;
  evidence: string[];
  recommendations: string[];
  confidence: number;
  requires_approval: boolean;
  draft_payload: Record<string, unknown>;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

interface ApprovalTask {
  id: string;
  output_id: string;
  assigned_role: string;
  status: 'pending' | 'approved' | 'rejected';
  decided_by: string;
  decided_at: string | null;
  notes: string;
  created_at: string;
}

// Chat models
interface Session {
  id: string;
  title: string;
  meta: string;
  kind: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  kind?: string;            // response routing: incident, knowledge, report, etc.
  artifacts?: Artifact[];
  rating?: RatingLevel;
  created_at: string;
}

interface Artifact {
  type: string;              // incident_card, rca_report, knowledge_draft, etc.
  data: Record<string, unknown>;
}

type RatingLevel = 'poor' | 'fair' | 'good' | 'great' | 'excellent';

// Chat API
interface ChatRequest {
  message: string;
  thread_id: string;
  role: string;
}

interface ChatResponse {
  kind: string;
  message: string;
  incident?: IncidentRecord;
  articles?: KnowledgeArticle[];
  incidents?: IncidentRecord[];
  problems?: ProblemRecord[];
  changes?: ChangeRecord[];
  report?: Record<string, unknown>;
  artifacts?: Artifact[];
  agent_outputs?: AgentOutput[];
  approval_tasks?: ApprovalTask[];
}

// Dashboard
interface DashboardSnapshot {
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

interface AuditEvent {
  kind: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

// Incidents overview
interface IncidentFilters {
  search: string;
  status: string;
  priority: string;
  timeWindow: string;
  page: number;
  pageSize: number;
}

interface IncidentsOverview {
  incidents: IncidentRecord[];
  sla_summary: SlaSummary;
  live_status: ConnectorHealth;
  pagination: PaginationMeta;
}

interface SlaSummary {
  response_compliance: number;
  resolution_compliance: number;
}

interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

// Settings
interface RuntimeSettings {
  naming: NamingSettings;
  connectors: ConnectorSettings;
  user_personas: Record<string, string>;
  agent_personas: Record<string, string>;
  general_instructions: GeneralInstructions;
  sla_targets: SlaTargets;
  kpi_targets: KpiTargets;
}

interface NamingSettings {
  brand_name: string;
  assistant_name: string;
  command_center_title: string;
  platform_title: string;
  sidebar_subtitle: string;
}

interface ConnectorSettings {
  servicenow: ServiceNowConfig;
  sharepoint: SharePointConfig;
  outlook: OutlookConfig;
  teams: TeamsConfig;
}

interface ConnectorHealth {
  connected: boolean;
  source: string;
  latency_ms: number | null;
  error: string | null;
}

interface ConnectorTestResult {
  status: 'success' | 'warning' | 'error' | 'pending';
  message: string;
}

// Auth
interface AuthUser {
  name: string;
  email: string;
  roles: string[];
}
```

---

## 7. Data Flow Summary

```
User interaction
  │
  ├── Navigation click → uiStore.setView() → re-render page component
  │
  ├── Chat submit → chatStore.addMessage() → api.post('/api/chat')
  │                 → response parsed by kind → MessageBubble or ArtifactCard
  │
  ├── Dashboard load → dashboardStore.fetchDashboard() → api.get('/api/dashboard')
  │                    → incidents, problems, changes, metrics populated
  │
  ├── Incident filter → dashboardStore.fetchIncidents(filters)
  │                     → api.get('/api/incidents/overview?...')
  │
  ├── Approval action → api.post('/api/approvals/{id}/decision')
  │                     → refresh dashboard
  │
  └── Settings save → settingsStore.saveSettings()
                      → api.put('/api/settings')
```
