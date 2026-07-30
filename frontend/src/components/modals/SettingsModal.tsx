import { useState, useEffect } from 'react';
import { useSettingsStore, ROLE_OPTIONS, AGENT_OPTIONS, defaultSettings } from '../../store/settingsStore';
import type { RuntimeSettings } from '../../types/api';

export default function SettingsModal() {
  const {
    settings,
    settingsOpen,
    activeTab,
    statusMessage,
    connectorTests,
    setSettingsOpen,
    setActiveTab,
    saveSettings,
    testConnector,
    loadSettings,
  } = useSettingsStore();

  const [form, setForm] = useState<RuntimeSettings>(defaultSettings());

  useEffect(() => {
    if (settingsOpen && !settings) loadSettings();
  }, [settingsOpen, settings, loadSettings]);

  useEffect(() => {
    if (settings) setForm(structuredClone(settings));
  }, [settings]);

  if (!settingsOpen) return null;

  const tabs = [
    { id: 'naming', label: 'Naming & Brand' },
    { id: 'user-personas', label: 'User Persona' },
    { id: 'agent-personas', label: 'Agent Persona' },
    { id: 'connectors', label: 'Connectors' },
    { id: 'metrics', label: 'Metrics & SLA' },
  ];

  const updateNaming = (key: string, value: string) =>
    setForm({ ...form, naming: { ...form.naming, [key]: value } });

  const handleSave = () => saveSettings(form);

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-[slideIn_0.2s_ease-out]" onClick={() => setSettingsOpen(false)}>
      <div className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl bg-[var(--surface)] border border-[var(--line)] shadow-[var(--shadow-lg)] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--line)]">
          <div>
            <h2 className="text-lg font-bold text-[var(--text)]">Settings</h2>
            <p className="text-[12px] text-[var(--muted)]">Configure platform behavior and integrations</p>
          </div>
          <button
            type="button"
            onClick={() => setSettingsOpen(false)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-6 py-2 border-b border-[var(--line)] overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-[var(--purple)] text-white'
                  : 'text-[var(--muted)] hover:bg-[var(--surface-soft)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {activeTab === 'naming' && (
            <div className="space-y-4">
              <FormField label="Brand Name" value={form.naming.brand_name} onChange={(v) => updateNaming('brand_name', v)} />
              <FormField label="Command Center Title" value={form.naming.command_center_title} onChange={(v) => updateNaming('command_center_title', v)} />
              <FormField label="Platform Title" value={form.naming.platform_title} onChange={(v) => updateNaming('platform_title', v)} />
              <FormField label="Sidebar Subtitle" value={form.naming.sidebar_subtitle} onChange={(v) => updateNaming('sidebar_subtitle', v)} />
            </div>
          )}

          {activeTab === 'user-personas' && (
            <div className="space-y-4">
              {ROLE_OPTIONS.map((role) => (
                <div key={role}>
                  <label className="text-[12px] font-semibold text-[var(--text)] mb-1 block">{role}</label>
                  <textarea
                    rows={3}
                    value={form.user_personas[role] || ''}
                    onChange={(e) => setForm({ ...form, user_personas: { ...form.user_personas, [role]: e.target.value } })}
                    className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-2 text-[13px] text-[var(--text)] focus:outline-none focus:border-[var(--purple)] resize-none"
                  />
                </div>
              ))}
            </div>
          )}

          {activeTab === 'agent-personas' && (
            <div className="space-y-4">
              {AGENT_OPTIONS.map(([key, label]) => (
                <div key={key}>
                  <label className="text-[12px] font-semibold text-[var(--text)] mb-1 block">{label}</label>
                  <textarea
                    rows={3}
                    value={form.agent_personas[key] || ''}
                    onChange={(e) => setForm({ ...form, agent_personas: { ...form.agent_personas, [key]: e.target.value } })}
                    className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-2 text-[13px] text-[var(--text)] focus:outline-none focus:border-[var(--purple)] resize-none"
                  />
                </div>
              ))}
              <div className="border-t border-[var(--line)] pt-4 space-y-4">
                <h3 className="text-sm font-bold text-[var(--text)]">General Instructions</h3>
                {(['platform', 'response_style', 'approval_policy'] as const).map((field) => (
                  <div key={field}>
                    <label className="text-[12px] font-semibold text-[var(--text)] mb-1 block capitalize">
                      {field.replace('_', ' ')}
                    </label>
                    <textarea
                      rows={2}
                      value={form.general_instructions[field]}
                      onChange={(e) => setForm({
                        ...form,
                        general_instructions: { ...form.general_instructions, [field]: e.target.value },
                      })}
                      className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-2 text-[13px] text-[var(--text)] focus:outline-none focus:border-[var(--purple)] resize-none"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'connectors' && (
            <div className="grid grid-cols-2 gap-4 max-[860px]:grid-cols-1">
              {/* ServiceNow */}
              <ConnectorCard
                title="ServiceNow"
                enabled={form.connectors.servicenow.enabled}
                onToggle={(v) => setForm({ ...form, connectors: { ...form.connectors, servicenow: { ...form.connectors.servicenow, enabled: v } } })}
                testResult={connectorTests['servicenow']}
                onTest={() => testConnector('servicenow')}
              >
                <FormField label="Base URL" value={form.connectors.servicenow.base_url} onChange={(v) => setForm({
                  ...form, connectors: { ...form.connectors, servicenow: { ...form.connectors.servicenow, base_url: v } },
                })} />
                <FormField label="Username" value={form.connectors.servicenow.username} onChange={(v) => setForm({
                  ...form, connectors: { ...form.connectors, servicenow: { ...form.connectors.servicenow, username: v } },
                })} />
              </ConnectorCard>

              {/* SharePoint */}
              <ConnectorCard
                title="SharePoint"
                enabled={form.connectors.sharepoint.enabled}
                onToggle={(v) => setForm({ ...form, connectors: { ...form.connectors, sharepoint: { ...form.connectors.sharepoint, enabled: v } } })}
                testResult={connectorTests['sharepoint']}
                onTest={() => testConnector('sharepoint')}
              >
                <FormField label="Site ID" value={form.connectors.sharepoint.site_id} onChange={(v) => setForm({
                  ...form, connectors: { ...form.connectors, sharepoint: { ...form.connectors.sharepoint, site_id: v } },
                })} />
              </ConnectorCard>

              {/* Outlook */}
              <ConnectorCard
                title="Outlook"
                enabled={form.connectors.outlook.enabled}
                onToggle={(v) => setForm({ ...form, connectors: { ...form.connectors, outlook: { ...form.connectors.outlook, enabled: v } } })}
                testResult={connectorTests['outlook']}
                onTest={() => testConnector('outlook')}
              >
                <FormField label="Sender" value={form.connectors.outlook.sender} onChange={(v) => setForm({
                  ...form, connectors: { ...form.connectors, outlook: { ...form.connectors.outlook, sender: v } },
                })} />
              </ConnectorCard>

              {/* Teams */}
              <ConnectorCard
                title="Teams"
                enabled={form.connectors.teams.enabled}
                onToggle={(v) => setForm({ ...form, connectors: { ...form.connectors, teams: { ...form.connectors.teams, enabled: v } } })}
                testResult={connectorTests['teams']}
                onTest={() => testConnector('teams')}
              >
                <FormField label="Team ID" value={form.connectors.teams.team_id} onChange={(v) => setForm({
                  ...form, connectors: { ...form.connectors, teams: { ...form.connectors.teams, team_id: v } },
                })} />
              </ConnectorCard>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-[var(--text)] mb-3">SLA Targets</h3>
                <div className="grid grid-cols-2 gap-3">
                  {['P1', 'P2', 'P3', 'P4'].map((p) => (
                    <div key={p} className="rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] p-3">
                      <h4 className="text-[12px] font-bold text-[var(--text)] mb-2">{p}</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] text-[var(--muted)]">Response (min)</label>
                          <input
                            type="number"
                            value={form.metrics.sla[p]?.response_minutes ?? ''}
                            onChange={(e) => setForm({
                              ...form,
                              metrics: {
                                ...form.metrics,
                                sla: { ...form.metrics.sla, [p]: { ...form.metrics.sla[p], response_minutes: Number(e.target.value) } },
                              },
                            })}
                            className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-2 py-1 text-[12px] text-[var(--text)] focus:outline-none focus:border-[var(--purple)]"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-[var(--muted)]">Resolution (hrs)</label>
                          <input
                            type="number"
                            value={form.metrics.sla[p]?.resolution_hours ?? ''}
                            onChange={(e) => setForm({
                              ...form,
                              metrics: {
                                ...form.metrics,
                                sla: { ...form.metrics.sla, [p]: { ...form.metrics.sla[p], resolution_hours: Number(e.target.value) } },
                              },
                            })}
                            className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-2 py-1 text-[12px] text-[var(--text)] focus:outline-none focus:border-[var(--purple)]"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-[var(--line)]">
          <span className="text-[12px] text-[var(--muted)]">{statusMessage}</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setSettingsOpen(false)}
              className="px-4 py-1.5 rounded-lg text-[12px] font-semibold bg-[var(--surface)] text-[var(--text)] border border-[var(--line)] hover:border-[var(--purple)] transition-all"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg text-[12px] font-semibold bg-[var(--purple)] text-white hover:bg-[var(--purple-hover)] transition-all shadow-sm"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FormField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-[12px] font-semibold text-[var(--text)] mb-1 block">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-2 text-[13px] text-[var(--text)] focus:outline-none focus:border-[var(--purple)] transition-all"
      />
    </div>
  );
}

function ConnectorCard({
  title,
  enabled,
  onToggle,
  testResult,
  onTest,
  children,
}: {
  title: string;
  enabled: boolean;
  onToggle: (v: boolean) => void;
  testResult?: { status: string; message: string };
  onTest: () => void;
  children: React.ReactNode;
}) {
  const statusColors: Record<string, string> = {
    success: 'text-[var(--green)]',
    warning: 'text-[var(--yellow)]',
    error: 'text-[var(--red)]',
    pending: 'text-[var(--muted)]',
  };

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-bold text-[var(--text)]">{title}</h3>
        <button
          type="button"
          onClick={() => onToggle(!enabled)}
          className={`w-10 h-5 rounded-full relative transition-all ${
            enabled ? 'bg-[var(--purple)]' : 'bg-[var(--line)]'
          }`}
        >
          <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${
            enabled ? 'left-5' : 'left-0.5'
          }`} />
        </button>
      </div>
      {children}
      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={onTest}
          className="px-3 py-1 rounded-lg text-[11px] font-semibold bg-[var(--surface)] text-[var(--text)] border border-[var(--line)] hover:border-[var(--purple)] transition-all"
        >
          Test Connection
        </button>
        {testResult && (
          <span className={`text-[11px] font-medium ${statusColors[testResult.status] || ''}`}>
            {testResult.message}
          </span>
        )}
      </div>
    </div>
  );
}
