import { create } from 'zustand';
import type { ViewType } from '../types/api';

interface UiState {
  currentView: ViewType;
  activeNav: string;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  activityFeedOpen: boolean;
  currentRole: string;
  profileMenuOpen: boolean;
  roleMenuOpen: boolean;
  supportPanelOpen: boolean;
  setView: (view: ViewType) => void;
  setActiveNav: (nav: string) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleActivityFeed: () => void;
  setActivityFeedOpen: (open: boolean) => void;
  setRole: (role: string) => void;
  setProfileMenuOpen: (open: boolean) => void;
  setRoleMenuOpen: (open: boolean) => void;
  setSupportPanelOpen: (open: boolean) => void;
  closeAllPanels: () => void;
}

const savedTheme = (localStorage.getItem('command-center-theme') as 'light' | 'dark') || 'light';
const savedRole = localStorage.getItem('command-center-role') || 'Support';

export const useUiStore = create<UiState>((set) => ({
  currentView: 'home',
  activeNav: 'home',
  theme: savedTheme,
  sidebarOpen: true,
  activityFeedOpen: true,
  currentRole: savedRole,
  profileMenuOpen: false,
  roleMenuOpen: false,
  supportPanelOpen: false,

  setView: (view) =>
    set({ currentView: view, activeNav: view === 'conversation' ? '' : view }),

  setActiveNav: (nav) => set({ activeNav: nav }),

  setTheme: (theme) => {
    localStorage.setItem('command-center-theme', theme);
    document.body.setAttribute('data-theme', theme);
    set({ theme });
  },

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleActivityFeed: () => set((s) => ({ activityFeedOpen: !s.activityFeedOpen })),
  setActivityFeedOpen: (open) => set({ activityFeedOpen: open }),

  setRole: (role) => {
    localStorage.setItem('command-center-role', role);
    set({ currentRole: role, roleMenuOpen: false });
  },

  setProfileMenuOpen: (open) => set({ profileMenuOpen: open }),
  setRoleMenuOpen: (open) => set({ roleMenuOpen: open, supportPanelOpen: false }),
  setSupportPanelOpen: (open) => set({ supportPanelOpen: open, roleMenuOpen: false }),

  closeAllPanels: () =>
    set({ profileMenuOpen: false, roleMenuOpen: false, supportPanelOpen: false }),
}));

// Apply saved theme on load
document.body.setAttribute('data-theme', savedTheme);
