import { useEffect } from 'react';
import Sidebar from './Sidebar';
import ActivityFeed from './ActivityFeed';
import { useUiStore } from '../../store/uiStore';

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * Responsive 3-panel layout with collapsible panels.
 *
 * At ≥860px  : Sidebar is an inline panel, animated between 240px ↔ 0.
 * At <860px  : Sidebar is an overlay drawer (slide-in from left).
 * At ≥1180px : ActivityFeed is an inline panel, animated between 280px ↔ 0.
 * At <1180px : ActivityFeed is an overlay drawer (slide-in from right).
 *
 * Toggle buttons are ALWAYS visible in WorkspaceHeader regardless of viewport.
 */
export default function AppShell({ children }: AppShellProps) {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const activityFeedOpen = useUiStore((s) => s.activityFeedOpen);
  const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);
  const setActivityFeedOpen = useUiStore((s) => s.setActivityFeedOpen);

  // Close overlay drawers on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSidebarOpen(false);
        setActivityFeedOpen(false);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [setSidebarOpen, setActivityFeedOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--page)] text-[var(--text)] font-[Segoe_UI,Aptos,system-ui,sans-serif]">

      {/* ── Sidebar — inline at ≥860px ──────────────── */}
      {/* Width transitions between 240px and 0 when toggled */}
      <div
        className={`
          hidden min-[860px]:flex flex-col shrink-0 overflow-hidden
          transition-[width] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
          ${sidebarOpen ? 'w-[240px]' : 'w-0'}
        `}
      >
        {/* Inner div never shrinks — prevents content from squishing during animation */}
        <div className="w-[240px] h-full flex flex-col">
          <Sidebar />
        </div>
      </div>

      {/* ── Workspace — always fills remaining space ── */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">{children}</main>

      {/* ── ActivityFeed — inline at ≥1180px ─────────── */}
      <div
        className={`
          hidden min-[1180px]:flex flex-col shrink-0 overflow-hidden
          transition-[width] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
          ${activityFeedOpen ? 'w-[280px]' : 'w-0'}
        `}
      >
        <div className="w-[280px] h-full flex flex-col">
          <ActivityFeed />
        </div>
      </div>

      {/* ── Sidebar overlay drawer (< 860px) ─────────── */}
      <div
        className={`
          fixed inset-0 z-50 min-[860px]:hidden
          transition-[visibility] duration-200
          ${sidebarOpen ? 'visible' : 'invisible'}
        `}
      >
        <div
          className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0'}`}
          onClick={() => setSidebarOpen(false)}
        />
        <div
          className={`
            absolute top-0 left-0 bottom-0 w-[280px] max-w-[85vw]
            bg-[var(--surface)] shadow-[var(--shadow-lg)]
            transition-transform duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          `}
        >
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </div>
      </div>

      {/* ── ActivityFeed overlay drawer (< 1180px) ────── */}
      <div
        className={`
          fixed inset-0 z-50 min-[1180px]:hidden
          transition-[visibility] duration-200
          ${activityFeedOpen ? 'visible' : 'invisible'}
        `}
      >
        <div
          className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${activityFeedOpen ? 'opacity-100' : 'opacity-0'}`}
          onClick={() => setActivityFeedOpen(false)}
        />
        <div
          className={`
            absolute top-0 right-0 bottom-0 w-[320px] max-w-[85vw]
            bg-[var(--surface)] shadow-[var(--shadow-lg)]
            transition-transform duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
            ${activityFeedOpen ? 'translate-x-0' : 'translate-x-full'}
          `}
        >
          <ActivityFeed onClose={() => setActivityFeedOpen(false)} />
        </div>
      </div>
    </div>
  );
}
