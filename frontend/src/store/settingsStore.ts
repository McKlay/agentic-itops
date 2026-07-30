import { create } from 'zustand';
import type { RuntimeSettings, ConnectorTestResult } from '../types/api';
import { api } from '../api/client';

interface SettingsState {
  settings: RuntimeSettings | null;
  connectorTests: Record<string, ConnectorTestResult>;
  settingsOpen: boolean;
  profileOpen: boolean;
  helpOpen: boolean;
  activeTab: string;
  statusMessage: string;

  loadSettings: () => Promise<void>;
  saveSettings: (settings: RuntimeSettings) => Promise<void>;
  testConnector: (name: string) => Promise<void>;
  setSettingsOpen: (open: boolean) => void;
  setProfileOpen: (open: boolean) => void;
  setHelpOpen: (open: boolean) => void;
  setActiveTab: (tab: string) => void;
  setStatusMessage: (message: string) => void;
}

export const ROLE_OPTIONS = [
  'Support',
  'Process Owner',
  'Application Owner',
  'Incident Manager',
  'Problem Manager',
  'Knowledge Manager',
  'Client Delivery Manager',
] as const;

export const AGENT_OPTIONS: [string, string][] = [
  ['orchestration_agent', 'SwiftAssist AI'],
  ['incident_agent', 'Incident Agent'],
  ['knowledge_agent', 'Knowledge Agent'],
  ['problem_agent', 'Problem / RCA Agent'],
  ['postmortem_agent', 'Blameless Postmortem Agent'],
  ['governance_agent', 'Monitoring & Governance Agent'],
];

export function defaultSettings(): RuntimeSettings {
  const brandName = 'SwiftAssist AI';
  const commandCenterTitle = `${brandName} Command Center`;
  return {
    naming: {
      brand_name: brandName,
      assistant_name: brandName,
      command_center_title: commandCenterTitle,
      platform_title: `${brandName} Platform`,
      sidebar_subtitle: 'Agentic IT Operations',
    },
    connectors: {
      servicenow: {
        enabled: true,
        base_url: '',
        default_domain: '',
        username: '',
        password: '',
        incident_page_limit: 200,
        verify_ssl: false,
      },
      sharepoint: { enabled: false, site_id: '', drive_id: '', repository: '' },
      outlook: { enabled: false, sender: '', recipients: '' },
      teams: { enabled: false, team_id: '', channel_id: '', approval_mode: 'approval_cards' },
    },
    user_personas: Object.fromEntries(
      ROLE_OPTIONS.map((role) => [
        role,
        `You are operating as the ${role} for ${commandCenterTitle}. Prioritize human-approved, approval-first guidance and communicate in concise operational terms.`,
      ])
    ),
    agent_personas: Object.fromEntries(
      AGENT_OPTIONS.map(([key, label]) => [
        key,
        `You are ${label} within ${commandCenterTitle}. Stay approval-first, evidence-based, and operationally concise.`,
      ])
    ),
    general_instructions: {
      platform: 'Preserve human accountability, governance, and operational safety.',
      response_style: 'Use concise operational language and call out uncertainty explicitly.',
      approval_policy: 'No autonomous remediation, closure, publication, or production changes are allowed.',
    },
    metrics: {
      sla: {
        P1: { response_minutes: 15, resolution_hours: 4 },
        P2: { response_minutes: 30, resolution_hours: 8 },
        P3: { response_minutes: 60, resolution_hours: 24 },
        P4: { response_minutes: 240, resolution_hours: 72 },
      },
      kpis: {
        mttr_target_hours: 8,
        first_contact_resolution_pct: 65,
        change_success_rate_pct: 95,
        knowledge_reuse_pct: 70,
        approval_sla_minutes: 30,
        csat_target_pct: 90,
      },
    },
  };
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  connectorTests: {},
  settingsOpen: false,
  profileOpen: false,
  helpOpen: false,
  activeTab: 'naming',
  statusMessage: '',

  loadSettings: async () => {
    try {
      const data = await api<RuntimeSettings>('/api/settings');
      set({ settings: data });
    } catch {
      set({ settings: defaultSettings() });
    }
  },

  saveSettings: async (settings) => {
    try {
      await api<RuntimeSettings>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      });
      set({ settings, statusMessage: 'Settings saved successfully.' });
    } catch {
      set({ statusMessage: 'Failed to save settings.' });
    }
  },

  testConnector: async (name) => {
    set((s) => ({
      connectorTests: { ...s.connectorTests, [name]: { status: 'pending', message: 'Testing...' } },
    }));
    try {
      const result = await api<ConnectorTestResult>(`/api/settings/test-connector/${name}`, {
        method: 'POST',
      });
      set((s) => ({
        connectorTests: { ...s.connectorTests, [name]: result },
      }));
    } catch {
      set((s) => ({
        connectorTests: { ...s.connectorTests, [name]: { status: 'error', message: 'Test failed.' } },
      }));
    }
  },

  setSettingsOpen: (open) => set({ settingsOpen: open }),
  setProfileOpen: (open) => set({ profileOpen: open }),
  setHelpOpen: (open) => set({ helpOpen: open }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setStatusMessage: (message) => set({ statusMessage: message }),
}));
