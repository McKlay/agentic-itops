import { useEffect } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import { useUiStore } from '../../store/uiStore';
import { IconShieldCheck, IconMenu, IconPanelRight } from '../shared/Icons';

export default function WorkspaceHeader() {
  const { dashboard, fetchDashboard } = useDashboardStore();
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const toggleActivityFeed = useUiStore((s) => s.toggleActivityFeed);
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const activityFeedOpen = useUiStore((s) => s.activityFeedOpen);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Derive system health from dashboard data
  const incidents = dashboard?.incidents || [];
  const criticalCount = incidents.filter(
    (i) => i.status === 'open' && (i.severity === 1 || i.severity === 2),
  ).length;

  const isHealthy = criticalCount === 0;
  const statusLabel = isHealthy ? 'System Healthy' : `${criticalCount} Critical`;
  const statusColor = isHealthy ? 'text-[var(--green)]' : 'text-[var(--red)]';
  const dotColor = isHealthy ? 'bg-[var(--green)]' : 'bg-[var(--red)]';

  return (
    <header className="flex items-center justify-between px-4 min-[860px]:px-6 py-3.5 border-b border-[var(--line)] bg-[var(--surface)] shrink-0 shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
      {/* Left section */}
      <div className="flex items-center gap-3">
        {/* Sidebar toggle — always visible */}
        <button
          type="button"
          onClick={toggleSidebar}
          className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
            sidebarOpen
              ? 'text-[var(--purple)] bg-[var(--surface-tint)]'
              : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)]'
          }`}
          aria-label="Toggle sidebar"
          aria-pressed={sidebarOpen}
        >
          <IconMenu size={18} />
        </button>
        <h1 className="text-[13px] font-semibold text-[var(--text)] tracking-tight">
          SwiftAssist AI Command Center
        </h1>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide ${statusColor}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dotColor} shrink-0`} />
          <IconShieldCheck size={12} />
          <span className="hidden min-[480px]:inline">{statusLabel}</span>
        </div>

        {/* Activity Feed toggle — always visible */}
        <button
          type="button"
          onClick={toggleActivityFeed}
          className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
            activityFeedOpen
              ? 'text-[var(--purple)] bg-[var(--surface-tint)]'
              : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)]'
          }`}
          aria-label="Toggle activity feed"
          aria-pressed={activityFeedOpen}
        >
          <IconPanelRight size={18} />
        </button>
      </div>
    </header>
  );
}
