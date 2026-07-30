import { useEffect, useState } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import StatusPill from '../shared/StatusPill';
import FilterChip from '../shared/FilterChip';

function addDays(dateStr: string, days: number): Date {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d;
}

function daysUntil(target: Date): number {
  return Math.max(0, Math.ceil((target.getTime() - Date.now()) / (1000 * 60 * 60 * 24)));
}

function dueColor(daysLeft: number): string {
  if (daysLeft <= 2) return 'text-[var(--red)] bg-[var(--red-soft)]';
  if (daysLeft <= 5) return 'text-[#b8860b] bg-[var(--yellow-soft)]';
  return 'text-[var(--green)] bg-[var(--green-soft)]';
}

const dueOptions = ['all', 'this_week'];

export default function ProblemsPage() {
  const { dashboard, fetchDashboard } = useDashboardStore();
  const [dueWindow, setDueWindow] = useState('all');

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const problems = dashboard?.problems || [];
  const filtered = dueWindow === 'this_week'
    ? problems.filter((p) => {
        const rcaDue = addDays(p.created_at, 7);
        return daysUntil(rcaDue) <= 7;
      })
    : problems;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-[var(--text)]">Problem Management</h1>
            <p className="text-[13px] text-[var(--muted)]">Track RCA and corrective action plan deadlines</p>
          </div>
          <FilterChip
            label="Due"
            options={dueOptions}
            value={dueWindow}
            onChange={setDueWindow}
          />
        </div>

        <div className="space-y-4">
          {filtered.map((problem) => {
            const rcaDue = addDays(problem.created_at, 7);
            const capDue = addDays(problem.created_at, 18);
            const rcaDays = daysUntil(rcaDue);
            const capDays = daysUntil(capDue);

            return (
              <div key={problem.id} className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-all">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-[15px] font-bold text-[var(--text)]">{problem.title}</h3>
                    <p className="text-[12px] text-[var(--muted)] mt-0.5">
                      {problem.id} · {problem.service} · {problem.linked_incidents.length} linked incident(s)
                    </p>
                  </div>
                  <StatusPill status={problem.status} />
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div className={`rounded-xl px-4 py-3 ${dueColor(rcaDays)}`}>
                    <h4 className="text-[11px] font-bold uppercase tracking-wider opacity-80 mb-1">RCA Due</h4>
                    <div className="text-sm font-bold">{rcaDue.toLocaleDateString()}</div>
                    <div className="text-[11px] mt-0.5">{rcaDays} day(s) remaining</div>
                  </div>
                  <div className={`rounded-xl px-4 py-3 ${dueColor(capDays)}`}>
                    <h4 className="text-[11px] font-bold uppercase tracking-wider opacity-80 mb-1">CAP Due</h4>
                    <div className="text-sm font-bold">{capDue.toLocaleDateString()}</div>
                    <div className="text-[11px] mt-0.5">{capDays} day(s) remaining</div>
                  </div>
                </div>

                <div className="mt-3 flex gap-2">
                  <button className="px-4 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--purple)] text-white hover:bg-[var(--purple-hover)] transition-all shadow-sm">
                    Generate RCA Report
                  </button>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-[var(--muted)] text-[13px]">No problems found</div>
          )}
        </div>
      </div>
    </div>
  );
}
