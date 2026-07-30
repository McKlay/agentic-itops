# Frontend Architecture

> **Last updated:** 2026-04-28  
> **Stack:** React 19 + Vite 8 + TypeScript 6 + Tailwind CSS 4 + Zustand 5  
> **Deployment:** Azure Static Web Apps  
> **Reference UI:** KnowledgeForge2 Command Center (`command_center.html`)

---

## 1. Overview

The frontend is a single-page application (SPA) that serves as the AI Operations Command Center. It runs identically in the browser and as a Microsoft Teams Personal Tab (iframe — no separate codebase). The backend API is a FastAPI service proxied via Vite in development.

### Tech Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | React 19 | Component model, ecosystem, Teams SDK compatibility |
| Build tool | Vite 8 | Fast HMR, native ESM, `@tailwindcss/vite` plugin |
| Styling | Tailwind CSS 4 | Utility-first, design token via CSS custom properties, no runtime CSS-in-JS |
| State management | Zustand 5 | Minimal boilerplate, no Context API overhead, works with React 19 |
| Type system | TypeScript 6 | Full type safety, interfaces mirror backend Pydantic models |

### Non-Negotiable Constraints

- **No CSS framework other than Tailwind** — no Bootstrap, Material UI, Ant Design
- **No Redux** — Zustand only for global state
- **No React Router** — view routing is state-driven via Zustand (`currentView` string)
- **No `fetch` outside `api/client.ts`** — all API calls go through the typed wrapper
- **`microsoftTeams.initialize()` called once in `main.tsx`** — never in components

---

## 2. Project Structure

```
frontend/
├── public/
│   └── manifest.json                # Teams Personal Tab manifest
├── src/
│   ├── api/
│   │   └── client.ts               # Typed fetch wrapper, Bearer token attachment
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx         # 3-panel CSS Grid shell
│   │   │   ├── Sidebar.tsx          # Navigation + sessions + role/theme/profile
│   │   │   └── ActivityFeed.tsx     # Right rail: live feed + metric strip
│   │   ├── chat/
│   │   │   ├── Conversation.tsx     # Scrollable message thread renderer
│   │   │   ├── Composer.tsx         # Input field + send + new/clear buttons
│   │   │   ├── MessageBubble.tsx    # User/assistant bubble with metadata
│   │   │   ├── ArtifactCard.tsx     # Rich structured cards (RCA, KB draft, incident)
│   │   │   └── ExperienceRating.tsx # 5-level emoji rating per response
│   │   ├── pages/
│   │   │   ├── HomePage.tsx         # Hero + 4 quick-action cards
│   │   │   ├── IncidentsPage.tsx    # Charts + paginated incident table
│   │   │   ├── ProblemsPage.tsx     # Problem cards with RCA/CAP SLA tracking
│   │   │   ├── ChangesPage.tsx      # Change table + 4-stage timeline
│   │   │   ├── ObservabilityPage.tsx# Service health grouped by domain
│   │   │   └── PerformancePage.tsx  # KPI cards + agent matrix table
│   │   ├── shared/
│   │   │   ├── StatusPill.tsx       # Colored status badge
│   │   │   ├── MetricTile.tsx       # Numeric KPI tile with label
│   │   │   ├── FeedCard.tsx         # Activity feed entry (color-coded)
│   │   │   ├── BarChart.tsx         # CSS div-based bar chart
│   │   │   ├── DonutChart.tsx       # CSS conic-gradient donut chart
│   │   │   ├── SlaGauge.tsx         # Track/fill SLA progress bar
│   │   │   ├── FilterChip.tsx       # Cycle-through filter buttons
│   │   │   ├── SearchInput.tsx      # Debounced search (250ms)
│   │   │   └── PaginationControls.tsx # Previous/Next pagination
│   │   └── modals/
│   │       ├── SettingsModal.tsx     # Full-screen overlay with 5 tab panels
│   │       ├── ProfileModal.tsx     # Compact profile card overlay
│   │       └── HelpModal.tsx        # Static help text overlay
│   ├── hooks/
│   │   ├── useThread.ts            # Create/fetch thread + messages
│   │   ├── useDashboard.ts         # Dashboard polling + incident filters
│   │   ├── useAuth.ts              # Entra ID token from SWA built-in auth
│   │   └── useSettings.ts          # Load/save runtime settings
│   ├── store/
│   │   ├── uiStore.ts              # View state, nav, theme, sidebar
│   │   ├── chatStore.ts            # Sessions, messages, conversation history
│   │   ├── dashboardStore.ts       # Dashboard snapshot, incidents, problems, changes
│   │   └── settingsStore.ts        # Runtime settings, connector states
│   ├── types/
│   │   └── api.ts                  # TS interfaces mirroring Pydantic models
│   ├── App.tsx                     # Root: AppShell + view dispatch
│   ├── main.tsx                    # Entry: Teams init + React root
│   └── index.css                   # @import "tailwindcss" + design tokens
├── staticwebapp.config.json         # SWA Entra ID auth routes
├── vite.config.ts                   # Tailwind plugin + /api proxy
├── tsconfig.json
├── eslint.config.js
├── package.json
└── docs/
    └── architecture/
        ├── FRONTEND-ARCHITECTURE.md     # This document
        └── COMPONENT-REFERENCE.md       # Detailed component specs
```

---

## 3. Layout — Three-Panel Grid

The UI replicates the KnowledgeForge2 Command Center layout:

```
┌──────────────────────────────────────────────────────────────┐
│  Sidebar (260px)  │  Workspace (fluid)  │  Activity (320px)  │
│                   │                     │                    │
│  Brand block      │  Header + health    │  Live Agent Feed   │
│  Navigation (6)   │  ─────────────────  │  (color-coded      │
│  Chat sessions    │  Page content or    │   feed cards)      │
│  ─────────────    │  conversation       │  ─────────────     │
│  Role switch      │                     │  Metric strip      │
│  Theme toggle     │  ─────────────────  │  (3 tiles)         │
│  Profile          │  Composer bar       │                    │
│  Powered by...    │                     │                    │
└──────────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Change |
|---|---|
| `< 1200px` | Chart grids → 1 column |
| `< 1180px` | Activity panel hides; sidebar shrinks to 220px |
| `< 860px` | Sidebar hides; single-column mobile layout |

### `AppShell.tsx`

```tsx
// Tailwind layout
<div className="grid grid-cols-[260px_1fr_320px] h-screen overflow-hidden">
  <Sidebar />
  <Workspace />
  <ActivityFeed />
</div>
```

---

## 4. View Routing (State-Driven)

Views are switched via the `currentView` property in `uiStore` — no URL routing.

| View | Component | Trigger |
|---|---|---|
| `home` | `HomePage` | Sidebar "Hub" nav click |
| `conversation` | `ConversationPage` | Chat input submission or session click |
| `incidents` | `IncidentsPage` | Sidebar "Incidents" nav click |
| `problems` | `ProblemsPage` | Sidebar "Problems" nav click |
| `changes` | `ChangesPage` | Sidebar "Changes" nav click |
| `observability` | `ObservabilityPage` | Sidebar "Observability" nav click |
| `performance` | `PerformancePage` | Sidebar "Agent Performance" nav click |

```tsx
// App.tsx — view dispatcher
function Workspace() {
  const currentView = useUiStore((s) => s.currentView);
  switch (currentView) {
    case 'home': return <HomePage />;
    case 'conversation': return <ConversationPage />;
    case 'incidents': return <IncidentsPage />;
    // ...
  }
}
```

---

## 5. State Management (Zustand)

### `uiStore` — UI Shell State

```typescript
interface UiState {
  currentView: ViewType;
  activeNav: string;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  setView: (view: ViewType) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
}
```

Persisted to `localStorage`: `theme`, `currentRole`.

### `chatStore` — Chat & Sessions

```typescript
interface ChatState {
  sessions: Session[];
  activeSessionId: string;
  conversations: Record<string, Message[]>;
  createSession: () => string;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  addMessage: (sessionId: string, message: Message) => void;
}
```

Session snapshots persisted to `localStorage` for cross-reload continuity.

### `dashboardStore` — Data Layer

```typescript
interface DashboardState {
  dashboard: DashboardSnapshot | null;
  incidents: IncidentRecord[];
  incidentFilters: IncidentFilters;
  loading: boolean;
  fetchDashboard: () => Promise<void>;
  fetchIncidents: (filters: IncidentFilters) => Promise<void>;
}
```

### `settingsStore` — Runtime Configuration

```typescript
interface SettingsState {
  settings: RuntimeSettings | null;
  connectorTests: Record<string, ConnectorTestResult>;
  loadSettings: () => Promise<void>;
  saveSettings: (settings: RuntimeSettings) => Promise<void>;
  testConnector: (name: string) => Promise<void>;
}
```

---

## 6. API Client

All API calls go through `src/api/client.ts`. This module:

1. Attaches `Authorization: Bearer <token>` from the auth hook
2. Sets `Content-Type: application/json`
3. Handles error responses consistently
4. Returns typed responses

```typescript
// src/api/client.ts
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) throw new ApiError(response.status, await response.json());
  return response.json();
}
```

### API Endpoints Consumed

| Endpoint | Method | Used By | Purpose |
|---|---|---|---|
| `/api/chat` | POST | `useThread` | Send chat message |
| `/api/dashboard` | GET | `useDashboard` | Full dashboard snapshot |
| `/api/incidents/overview` | GET | `useDashboard` | Filtered/paginated incidents |
| `/api/approvals/{id}/decision` | POST | `ArtifactCard` | Submit approval decision |
| `/api/supervisor/problems/{id}/rca-report` | POST | `ProblemsPage` | Generate RCA report |
| `/api/supervisor/incidents/{id}/knowledge-draft` | POST | `ArtifactCard` | Create KB draft |
| `/api/settings` | GET/PUT | `useSettings` | Load/save settings |
| `/api/settings/test-connector/{name}` | POST | `SettingsModal` | Test connector |

---

## 7. Authentication

### Azure Static Web Apps Built-in Auth

```json
// staticwebapp.config.json
{
  "auth": {
    "identityProviders": {
      "azureActiveDirectory": {
        "registration": {
          "openIdIssuer": "https://login.microsoftonline.com/<TENANT_ID>/v2.0",
          "clientIdSettingName": "ENTRA_CLIENT_ID",
          "clientSecretSettingName": "ENTRA_CLIENT_SECRET"
        }
      }
    }
  },
  "routes": [
    { "route": "/api/*", "allowedRoles": ["authenticated"] },
    { "route": "/v1/*", "allowedRoles": ["authenticated"] },
    { "route": "/healthz", "allowedRoles": ["anonymous"] }
  ]
}
```

### `useAuth` Hook

```typescript
function useAuth() {
  // SWA exposes /.auth/me for the logged-in user
  const [user, setUser] = useState<AuthUser | null>(null);
  useEffect(() => {
    fetch('/.auth/me').then(r => r.json()).then(data => {
      const principal = data.clientPrincipal;
      if (principal) setUser({ name: principal.userDetails, roles: principal.userRoles });
    });
  }, []);
  return user;
}
```

### Teams Personal Tab

```tsx
// src/main.tsx
import * as microsoftTeams from "@microsoft/teams-js";
microsoftTeams.initialize();

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
```

No rendering differences — Teams renders the identical HTML/CSS output via iframe.

---

## 8. Design Tokens (Tailwind CSS Custom Properties)

Design tokens are defined as CSS custom properties in `index.css` and consumed via Tailwind's `var()` references. The system supports light and dark themes.

### Light Theme (`:root`)

```css
:root {
  --page: #f5f6fb;
  --surface: #ffffff;
  --surface-soft: #f7f8fc;
  --surface-tint: #f3eefe;
  --line: #ececf3;
  --line-strong: #e4ddf8;
  --text: #1f2533;
  --muted: #70778c;
  --purple: #7d48ff;
  --purple-soft: #efe7ff;
  --green: #18a957;
  --green-soft: #ebfff2;
  --red: #ef6a6a;
  --red-soft: #fff0f0;
  --yellow: #f3b741;
  --yellow-soft: #fff8e8;
  --blue-soft: #dbeafe;
  --pink-soft: #ffe1e1;
  --mint-soft: #d9f8ee;
  --lavender-soft: #ecdfff;
}
```

### Dark Theme (via `data-theme="dark"` on `<body>`)

```css
body[data-theme="dark"] {
  --page: #0d1220;
  --surface: #161d30;
  --surface-soft: #20283d;
  --surface-tint: #231c3c;
  --line: #2c3450;
  --line-strong: #433760;
  --text: #edf1ff;
  --muted: #a4aec8;
  --purple-soft: #2a2148;
  --green-soft: #133727;
  --red-soft: #3d2025;
  --yellow-soft: #392d17;
  --blue-soft: #1b2f58;
  --pink-soft: #41242b;
  --mint-soft: #173a34;
  --lavender-soft: #2b2346;
}
```

### Font

```css
font-family: "Segoe UI", "Aptos", system-ui, sans-serif;
```

---

## 9. Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/v1': 'http://localhost:8000',
    },
  },
});
```

- Tailwind via `@tailwindcss/vite` plugin — **not** PostCSS
- Proxy `/api/*` and `/v1/*` to the backend at `:8000` during development

---

## 10. TypeScript Interfaces

Interfaces in `src/types/api.ts` must mirror backend Pydantic models exactly.

```typescript
// Key interfaces (see COMPONENT-REFERENCE.md for full list)
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
  resolved_at: string | null;
}

interface MessageRecord {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

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
  status: 'pending' | 'approved' | 'rejected';
}

interface ChatResponse {
  kind: string;
  message: string;
  artifacts?: Artifact[];
  agent_outputs?: AgentOutput[];
  approval_tasks?: ApprovalTask[];
}
```

---

## 11. Deployment

### Azure Static Web Apps

```yaml
# .github/workflows/deploy-frontend.yml
on:
  push:
    branches: [main]
    paths: ["frontend/**"]

jobs:
  deploy:
    steps:
      - uses: Azure/static-web-apps-deploy@v1
        with:
          app_location: "frontend"
          output_location: "dist"
          skip_api_build: true     # API is App Service, not SWA Functions
```

### Local Development

```bash
cd frontend && npm run dev     # Vite dev server at :5173, proxies /api → :8000
```

---

## 12. Coding Conventions

| Convention | Rule |
|---|---|
| **Component files** | `.tsx` extension, PascalCase filename matching export name |
| **Hook files** | `.ts` extension, `use` prefix (e.g. `useThread.ts`) |
| **State files** | `.ts` extension, `Store` suffix (e.g. `uiStore.ts`) |
| **Imports** | Absolute from `src/` root — configure `paths` in `tsconfig.json` if needed |
| **Props** | Defined as interface above the component, named `{Component}Props` |
| **Linter** | ESLint with `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh` |
| **No inline styles** | Tailwind utility classes only; CSS custom properties for design tokens |
| **No `any` types** | Use `unknown` when type is uncertain; define proper interfaces |
