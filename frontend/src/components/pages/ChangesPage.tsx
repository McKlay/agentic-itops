import { useEffect } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import StatusPill from '../shared/StatusPill';
import { formatDate } from '../../utils/helpers';

const timelineStages = ['Draft', 'Review', 'Approved', 'Implemented'];

function stageIndex(status: string): number {
  const map: Record<string, number> = {
    draft: 0,
    review: 1,
    approved: 2,
    implemented: 3,
  };
  return map[status.toLowerCase()] ?? 0;
}

export default function ChangesPage() {
  const { dashboard, fetchDashboard } = useDashboardStore();

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const changes = dashboard?.changes || [];

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-[var(--text)]">Change Management</h1>
          <p className="text-[13px] text-[var(--muted)]">Track change requests and implementation progress</p>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-sm)]">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[var(--line)] bg-[var(--surface-soft)]">
                {['ID', 'Title', 'Service', 'Status', 'Rationale', 'Created', 'Progress'].map((h) => (
                  <th key={h} className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {changes.map((change) => {
                const currentStage = stageIndex(change.status);
                return (
                  <tr key={change.id} className="border-b border-[var(--line)] hover:bg-[var(--surface-soft)] transition-colors">
                    <td className="px-4 py-3 text-[12px] font-mono text-[var(--purple)]">{change.id}</td>
                    <td className="px-4 py-3 text-[13px] text-[var(--text)] max-w-[180px] truncate">{change.title}</td>
                    <td className="px-4 py-3 text-[12px] text-[var(--muted)]">{change.service}</td>
                    <td className="px-4 py-3"><StatusPill status={change.status} /></td>
                    <td className="px-4 py-3 text-[12px] text-[var(--muted)] max-w-[150px] truncate">{change.rationale}</td>
                    <td className="px-4 py-3 text-[12px] text-[var(--muted)]">{formatDate(change.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        {timelineStages.map((stage, i) => (
                          <span
                            key={stage}
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              i <= currentStage
                                ? 'bg-[var(--purple)] text-white'
                                : 'bg-[var(--surface-soft)] text-[var(--muted)]'
                            }`}
                          >
                            {stage}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {changes.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-[var(--muted)] text-[13px]">
                    No changes found
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
