import { create } from 'zustand';
import type {
  DashboardSnapshot,
  IncidentRecord,
  IncidentFilters,
  SlaSummary,
  ConnectorHealth,
  PaginationMeta,
} from '../types/api';
import { api } from '../api/client';

interface DashboardState {
  dashboard: DashboardSnapshot | null;
  incidents: IncidentRecord[];
  incidentFilters: IncidentFilters;
  slaSummary: SlaSummary | null;
  liveStatus: ConnectorHealth | null;
  pagination: PaginationMeta | null;
  loading: boolean;

  fetchDashboard: (force?: boolean) => Promise<void>;
  fetchIncidents: (filters?: Partial<IncidentFilters>) => Promise<void>;
  setIncidentFilters: (filters: Partial<IncidentFilters>) => void;
}

const defaultFilters: IncidentFilters = {
  search: '',
  status: 'all',
  priority: 'all',
  timeWindow: 'all',
  page: 1,
  pageSize: 100,
};

export const useDashboardStore = create<DashboardState>((set, get) => ({
  dashboard: null,
  incidents: [],
  incidentFilters: { ...defaultFilters },
  slaSummary: null,
  liveStatus: null,
  pagination: null,
  loading: false,

  fetchDashboard: async (force = false) => {
    set({ loading: true });
    try {
      const url = force ? '/api/dashboard?refresh=true' : '/api/dashboard';
      const data = await api<DashboardSnapshot>(url);
      set({ dashboard: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchIncidents: async (filterOverrides) => {
    const state = get();
    const filters = { ...state.incidentFilters, ...filterOverrides };
    set({ incidentFilters: filters, loading: true });

    try {
      const params = new URLSearchParams();
      if (filters.search) params.set('search', filters.search);
      if (filters.status !== 'all') params.set('status', filters.status);
      if (filters.priority !== 'all') params.set('priority', filters.priority);
      if (filters.timeWindow !== 'all') params.set('time_window', filters.timeWindow);
      params.set('page', String(filters.page));
      params.set('page_size', String(filters.pageSize));

      const data = await api<{
        incidents: IncidentRecord[];
        sla_summary: SlaSummary;
        live_status: ConnectorHealth;
        pagination: PaginationMeta;
      }>(`/api/incidents/overview?${params}`);

      set({
        incidents: data.incidents,
        slaSummary: data.sla_summary,
        liveStatus: data.live_status,
        pagination: data.pagination,
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },

  setIncidentFilters: (filters) => {
    set((s) => ({
      incidentFilters: { ...s.incidentFilters, ...filters },
    }));
  },
}));
