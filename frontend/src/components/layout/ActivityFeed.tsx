import { useEffect } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import FeedCard from '../shared/FeedCard';
import MetricTile from '../shared/MetricTile';
import { IconRadioTower, IconX } from '../shared/Icons';
import type { FeedType, AuditEvent } from '../../types/api';
import { nowTime } from '../../utils/helpers';

interface ActivityFeedProps {
  /** Called when the user taps the close button (drawer mode only). */
  onClose?: () => void;
}

function mapAuditToFeed(event: AuditEvent): { type: FeedType; agent: string; time: string; description: string } {
  const kind = event.kind || '';
  let type: FeedType = 'orchestration';
  if (kind.includes('incident')) type = 'incident';
  else if (kind.includes('monitoring') || kind.includes('telemetry')) type = 'monitoring';
  else if (kind.includes('problem')) type = 'problem';

  const agent = String(event.payload?.agent_name || event.payload?.agent_id || 'System');
  const description = String(event.payload?.summary || event.payload?.title || kind);
  const time = event.timestamp
    ? new Date(event.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    : nowTime();

  return { type, agent, time, description };
}

export default function ActivityFeed({ onClose }: ActivityFeedProps) {
  const { dashboard, fetchDashboard } = useDashboardStore();

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const auditLog = dashboard?.audit_log || [];
  const feedItems = auditLog.slice(0, 20).map(mapAuditToFeed);

  const openIncidents = dashboard?.incidents?.filter((i) => i.status === 'open').length || 0;
  const pendingApprovals = dashboard?.approvals?.filter((a) => a.status === 'pending').length || 0;
  const mttr = dashboard?.metrics?.mttr_hours;
  const mttrDisplay = typeof mttr === 'number' ? `${mttr.toFixed(1)}h` : '—';

  return (
    <aside className="flex flex-col h-full bg-[var(--surface)] border-l border-[var(--line)] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[var(--line)] shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
        <h2 className="text-[13px] font-bold text-[var(--text)] tracking-tight">Live Agent Feed</h2>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[var(--green-soft)]">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--green)] opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[var(--green)]" />
            </span>
            <span className="text-[9px] font-bold text-[var(--green)] uppercase tracking-wider">Live</span>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
              aria-label="Close activity feed"
            >
              <IconX size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {feedItems.length > 0 ? (
          feedItems.map((item, i) => (
            <FeedCard key={i} {...item} />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-10 h-10 rounded-xl bg-[var(--surface-soft)] border border-[var(--line)] flex items-center justify-center mb-3">
              <IconRadioTower size={18} className="text-[var(--muted)] opacity-50" />
            </div>
            <p className="text-[12px] font-medium text-[var(--text)] mb-0.5">No agent activity yet</p>
            <p className="text-[10px] text-[var(--muted)] leading-snug max-w-[180px]">
              Agent events will appear here in real time as they process incidents and tasks.
            </p>
          </div>
        )}
      </div>

      {/* Metric Strip */}
      <div className="grid grid-cols-3 gap-1 px-2 py-2 border-t border-[var(--line)] bg-[var(--surface)]">
        <MetricTile label="Incidents" value={openIncidents} accent={openIncidents > 0 ? 'text-[var(--red)]' : undefined} />
        <MetricTile label="Approvals" value={pendingApprovals} accent={pendingApprovals > 0 ? 'text-[var(--yellow)]' : undefined} />
        <MetricTile label="MTTR" value={mttrDisplay} accent="text-[var(--green)]" />
      </div>
    </aside>
  );
}
