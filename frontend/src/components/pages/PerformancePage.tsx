import { useEffect } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import { formatPercentage } from '../../utils/helpers';

const kpiDefinitions = [
  { key: 'mttr_hours', label: 'Mean Time to Resolve', unit: 'hours', format: (v: number) => `${v.toFixed(1)}h` },
  { key: 'first_contact_resolution', label: 'First Contact Resolution', unit: '%', format: (v: number) => formatPercentage(v) },
  { key: 'change_success_rate', label: 'Change Success Rate', unit: '%', format: (v: number) => formatPercentage(v) },
  { key: 'knowledge_reuse_rate', label: 'Knowledge Reuse Rate', unit: '%', format: (v: number) => formatPercentage(v) },
  { key: 'approval_sla_compliance', label: 'Approval SLA Compliance', unit: '%', format: (v: number) => formatPercentage(v) },
  { key: 'csat', label: 'Customer Satisfaction', unit: '/5', format: (v: number) => `${v.toFixed(1)}/5` },
  { key: 'adoption_rate', label: 'Adoption Rate', unit: '%', format: (v: number) => formatPercentage(v) },
  { key: 'hours_saved', label: 'Hours Saved', unit: 'hrs/mo', format: (v: number) => `${Math.round(v)} hrs/mo` },
];

interface AgentRow {
  name: string;
  metrics: Record<string, number>;
}

export default function PerformancePage() {
  const { dashboard, fetchDashboard } = useDashboardStore();

  useEffect(() => {
    fetchDashboard(true);
  }, [fetchDashboard]);

  const metrics = (dashboard?.metrics || {}) as Record<string, unknown>;

  // Build agent matrix
  const agents = (dashboard?.agents || []) as unknown as AgentRow[];

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-[var(--text)]">Agent Performance</h1>
          <p className="text-[13px] text-[var(--muted)]">Key performance indicators and agent effectiveness matrix</p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-3 max-[1200px]:grid-cols-2">
          {kpiDefinitions.map((kpi) => {
            const rawValue = metrics[kpi.key];
            const value = typeof rawValue === 'number' ? rawValue : 0;
            return (
              <div key={kpi.key} className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]">
                <div className="text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-2">
                  {kpi.label}
                </div>
                <div className="text-2xl font-bold text-[var(--text)]">
                  {kpi.format(value)}
                </div>
              </div>
            );
          })}
        </div>

        {/* Agent Matrix */}
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-sm)]">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[var(--line)] bg-[var(--surface-soft)]">
                <th className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">Agent</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">Accuracy</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">Avg Response</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">Tasks</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">Approval Rate</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.name} className="border-b border-[var(--line)] hover:bg-[var(--surface-soft)] transition-colors">
                  <td className="px-4 py-3 text-[13px] font-semibold text-[var(--text)]">{agent.name}</td>
                  <td className="px-4 py-3">
                    <ProgressBar value={Number(agent.metrics?.accuracy || 0)} />
                  </td>
                  <td className="px-4 py-3 text-[12px] text-[var(--muted)]">
                    {agent.metrics?.avg_response_ms ? `${agent.metrics.avg_response_ms}ms` : '—'}
                  </td>
                  <td className="px-4 py-3 text-[12px] text-[var(--text)] font-medium">
                    {agent.metrics?.total_tasks ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    <ProgressBar value={Number(agent.metrics?.approval_rate || 0)} />
                  </td>
                </tr>
              ))}
              {agents.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted)] text-[13px]">
                    No agent data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.min(Math.max(value, 0), 100);
  const color =
    pct >= 80 ? 'bg-[var(--green)]' :
    pct >= 60 ? 'bg-[var(--yellow)]' :
    'bg-[var(--red)]';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-[var(--surface-soft)] overflow-hidden max-w-[80px]">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-semibold text-[var(--text)]">{pct.toFixed(0)}%</span>
    </div>
  );
}
