import { useState } from 'react';
import type { ReactNode } from 'react';
import { useUiStore } from '../../store/uiStore';
import { useChatStore } from '../../store/chatStore';
import { useSettingsStore, ROLE_OPTIONS } from '../../store/settingsStore';
import { profileInitials } from '../../utils/helpers';
import {
  IconGrid, IconCircleDot, IconTarget, IconArrowsLR, IconActivity, IconGear,
  IconPlus, IconPencil, IconX, IconSwitch, IconSun, IconMoon,
  IconUser, IconPalette, IconHelpCircle, IconLogOut, IconChevronLeft,
} from '../shared/Icons';
import type { ViewType } from '../../types/api';

interface SidebarProps {
  /** Called when the user taps the close button (drawer mode only). */
  onClose?: () => void;
}

const navItems: { label: string; icon: ReactNode; view: ViewType }[] = [
  { label: 'Hub', icon: <IconGrid size={16} />, view: 'home' },
  { label: 'Incidents', icon: <IconCircleDot size={16} />, view: 'incidents' },
  { label: 'Problems', icon: <IconTarget size={16} />, view: 'problems' },
  { label: 'Changes', icon: <IconArrowsLR size={16} />, view: 'changes' },
  { label: 'Observability', icon: <IconActivity size={16} />, view: 'observability' },
  { label: 'Agent Performance', icon: <IconGear size={16} />, view: 'performance' },
];

export default function Sidebar({ onClose }: SidebarProps) {
  const { currentView, setView, theme, setTheme, currentRole, setRole, activeNav } = useUiStore();
  const {
    sessions,
    activeSessionId,
    switchSession,
    createSession,
    deleteSession,
    renameSession,
  } = useChatStore();
  const { setSettingsOpen, setProfileOpen, setHelpOpen } = useSettingsStore();

  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [supportPanelOpen, setSupportPanelOpen] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const brandName = 'SwiftAssist AI';
  const userName = 'John Doe';

  const handleNav = (view: ViewType) => {
    setView(view);
    setProfileMenuOpen(false);
    setRoleMenuOpen(false);
    setSupportPanelOpen(false);
    onClose?.();
  };

  const handleNewSession = () => {
    const id = createSession();
    switchSession(id);
    setView('conversation');
    onClose?.();
  };

  const handleStartRename = (id: string, currentTitle: string) => {
    setEditingSessionId(id);
    setEditTitle(currentTitle);
  };

  const handleFinishRename = (id: string) => {
    if (editTitle.trim()) renameSession(id, editTitle.trim());
    setEditingSessionId(null);
  };

  return (
    <aside className="flex flex-col h-full bg-[var(--surface)] border-r border-[var(--line)] overflow-hidden">
      {/* Brand */}
      <div className="flex items-center justify-between px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--purple)] to-[#a855f7] flex items-center justify-center shadow-md">
            <span className="text-white text-sm font-bold">S</span>
          </div>
          <div>
            <div className="text-sm font-bold text-[var(--text)] leading-tight">{brandName}</div>
            <div className="text-[11px] text-[var(--muted)] font-medium">Agentic IT Operations</div>
          </div>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
            aria-label="Close sidebar"
          >
            <IconChevronLeft size={16} />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="px-2 space-y-0.5">
        {navItems.map((item) => {
          const isActive = activeNav === item.view || (item.view === 'home' && currentView === 'home' && !activeNav);
          return (
            <button
              key={item.view}
              type="button"
              onClick={() => handleNav(item.view)}
              className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13px] transition-all duration-[var(--transition-fast)] ${
                isActive
                  ? 'bg-[var(--surface-soft)] text-[var(--purple)] font-semibold'
                  : 'text-[var(--text)] hover:bg-[var(--surface-soft)] font-medium'
              }`}
            >
              <span className="w-4 shrink-0 opacity-70">{item.icon}</span>
              <span>{item.view === 'home' ? `${brandName} Hub` : item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Chat Sessions */}
      <div className="flex-1 flex flex-col mt-3 border-t border-[var(--line)] overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
            Chat Sessions
          </span>
          <button
            type="button"
            onClick={handleNewSession}
            className="w-6 h-6 rounded-md flex items-center justify-center text-[var(--muted)] hover:bg-[var(--surface-soft)] hover:text-[var(--purple)] transition-all"
          >
            <IconPlus size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => {
                switchSession(session.id);
                setView('conversation');
                onClose?.();
              }}
              className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-all duration-[var(--transition-fast)] ${
                activeSessionId === session.id
                  ? 'bg-[var(--surface-soft)]'
                  : 'hover:bg-[var(--surface-soft)]'
              }`}
            >
              <div className="flex-1 min-w-0">
                {editingSessionId === session.id ? (
                  <input
                    autoFocus
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleFinishRename(session.id)}
                    onKeyDown={(e) => e.key === 'Enter' && handleFinishRename(session.id)}
                    className="w-full text-[13px] bg-transparent border-b border-[var(--purple)] outline-none text-[var(--text)]"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <div className="text-[13px] font-medium text-[var(--text)] truncate">{session.title}</div>
                    <div className="text-[11px] text-[var(--muted)]">{session.meta}</div>
                  </>
                )}
              </div>
              <div className="hidden group-hover:flex items-center gap-1 ml-2 shrink-0">
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleStartRename(session.id, session.title); }}
                  className="w-5 h-5 rounded text-[var(--muted)] hover:text-[var(--purple)] hover:bg-[var(--surface-tint)] flex items-center justify-center"
                  title="Rename"
                >
                  <IconPencil size={12} />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                  className="w-5 h-5 rounded text-[var(--muted)] hover:text-[var(--red)] hover:bg-[var(--red-soft)] flex items-center justify-center"
                  title="Delete"
                >
                  <IconX size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--line)] px-3 py-3 space-y-2">
        {/* Role Switch */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setRoleMenuOpen(!roleMenuOpen)}
            className="flex-1 flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-medium text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
          >
            <IconSwitch size={14} className="opacity-60" />
            Switch Role
          </button>
          <button
            type="button"
            onClick={() => setSupportPanelOpen(!supportPanelOpen)}
            className="px-3 py-1.5 rounded-full text-[11px] font-semibold bg-[var(--surface-soft)] text-[var(--muted)] hover:text-[var(--purple)] border border-[var(--line)] transition-all"
          >
            {currentRole}
          </button>
        </div>

        {/* Support Panel */}
        {supportPanelOpen && (
          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-soft)] p-3 animate-[slideIn_0.2s_ease-out]">
            <p className="text-[12px] text-[var(--muted)] mb-2">
              Current operating role: <strong className="text-[var(--text)]">{currentRole}</strong>
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className="px-3 py-1 rounded-lg text-[11px] font-semibold bg-[var(--purple)] text-white hover:bg-[var(--purple-hover)] transition-all"
              >
                Open incidents
              </button>
              <button
                type="button"
                className="px-3 py-1 rounded-lg text-[11px] font-semibold bg-[var(--surface)] text-[var(--text)] border border-[var(--line)] hover:border-[var(--purple)] transition-all"
              >
                Pending approvals
              </button>
            </div>
          </div>
        )}

        {/* Role Menu */}
        {roleMenuOpen && (
          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-1.5 shadow-[var(--shadow-md)] animate-[slideIn_0.2s_ease-out]">
            {ROLE_OPTIONS.map((role) => (
              <button
                key={role}
                type="button"
                onClick={() => { setRole(role); setRoleMenuOpen(false); }}
                className={`w-full text-left px-3 py-1.5 rounded-lg text-[12px] transition-all ${
                  currentRole === role
                    ? 'bg-[var(--surface-tint)] text-[var(--purple)] font-semibold'
                    : 'text-[var(--text)] hover:bg-[var(--surface-soft)]'
                }`}
              >
                {role}
              </button>
            ))}
          </div>
        )}

        {/* Theme Switcher */}
        <div className="flex rounded-lg border border-[var(--line)] overflow-hidden">
          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`flex-1 py-1.5 text-[11px] font-semibold transition-all flex items-center justify-center gap-1 ${
              theme === 'light'
                ? 'bg-[var(--surface-tint)] text-[var(--purple)]'
                : 'text-[var(--muted)] hover:text-[var(--text)]'
            }`}
          >
            <IconSun size={12} /> Light
          </button>
          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`flex-1 py-1.5 text-[11px] font-semibold transition-all flex items-center justify-center gap-1 ${
              theme === 'dark'
                ? 'bg-[var(--surface-tint)] text-[var(--purple)]'
                : 'text-[var(--muted)] hover:text-[var(--text)]'
            }`}
          >
            <IconMoon size={12} /> Dark
          </button>
        </div>

        {/* Profile */}
        {profileMenuOpen && (
          <div className="fixed inset-0 z-40" onClick={() => setProfileMenuOpen(false)} />
        )}
        <div className="relative">
          <button
            type="button"
            onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            className="w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-[var(--surface-soft)] transition-all"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#7d48ff] to-[#a855f7] flex items-center justify-center text-white text-xs font-bold shadow-sm">
              {profileInitials(userName)}
            </div>
            <span className="text-[13px] font-medium text-[var(--text)]">{userName}</span>
          </button>

          {profileMenuOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-1 rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow-lg)] z-50 overflow-hidden animate-[slideIn_0.15s_ease-out]">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--line)]">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#7d48ff] to-[#a855f7] flex items-center justify-center text-white text-xs font-bold">
                  {profileInitials(userName)}
                </div>
                <div>
                  <div className="text-[13px] font-semibold text-[var(--text)]">{userName}</div>
                  <div className="text-[11px] text-[var(--muted)]">Logged in · {currentRole}</div>
                </div>
              </div>
              <div className="p-1">
                {[
                  { icon: <IconUser size={14} />, label: 'Profile', action: () => { setProfileOpen(true); setProfileMenuOpen(false); } },
                  { icon: <IconPalette size={14} />, label: 'Personalization', action: () => { setSettingsOpen(true); setProfileMenuOpen(false); } },
                  { icon: <IconGear size={14} />, label: 'Settings', action: () => { setSettingsOpen(true); setProfileMenuOpen(false); } },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={item.action}
                    className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13px] text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
                  >
                    <span className="opacity-50">{item.icon}</span>
                    {item.label}
                  </button>
                ))}
                <div className="h-px bg-[var(--line)] my-1" />
                <button
                  type="button"
                  onClick={() => { setHelpOpen(true); setProfileMenuOpen(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13px] text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
                >
                  <IconHelpCircle size={14} className="opacity-50" />
                  Help
                </button>
                <button
                  type="button"
                  className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13px] text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
                >
                  <IconLogOut size={14} className="opacity-50" />
                  Log out
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="text-[10px] text-[var(--muted)] text-center pt-1">
          Powered by Azure OpenAI
        </div>
      </div>
    </aside>
  );
}
