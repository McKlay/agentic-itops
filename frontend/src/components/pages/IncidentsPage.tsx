import { useEffect, useCallback } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import SearchInput from '../shared/SearchInput';
import FilterChip from '../shared/FilterChip';
import BarChart from '../shared/BarChart';
import DonutChart from '../shared/DonutChart';
import SlaGauge from '../shared/SlaGauge';
import PaginationControls from '../shared/PaginationControls';
import StatusPill from '../shared/StatusPill';
import { priorityLabel, formatDate } from '../../utils/helpers';

const statusOptions = ['all', 'open', 'in_progress', 'resolved', 'closed'];
const priorityOptions = ['all', 'P1', 'P2', 'P3', 'P4'];
const timeOptions = ['all', 'this_week', 'this_month', 'last_30_days'];

export default function IncidentsPage() {
  const {
    incidents,
    incidentFilters,
    slaSummary,
    liveStatus,
    pagination,
    loading,
    fetchIncidents,
    setIncidentFilters,
  } = useDashboardStore();

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const handleSearch = useCallback(
    (query: string) => {
      setIncidentFilters({ search: query, page: 1 });
      fetchIncidents({ search: query, page: 1 });
    },
    [fetchIncidents, setIncidentFilters]
  );

  const handleFilterChange = (key: string, value: string) => {
    const update = { [key]: value, page: 1 };
    setIncidentFilters(update);
    fetchIncidents(update);
  };

  const handlePageChange = (page: number) => {
    setIncidentFilters({ page });
    fetchIncidents({ page });
  };

  // Chart data
  const priorityCounts = [1, 2, 3, 4].map((sev) => ({
    label: `P${sev}`,
    value: incidents.filter((i) => i.severity === sev).length,
    color: ['#d54f4f', '#f0ad35', '#3a74f5', '#14c38e'][sev - 1],
  }));

  const statusCounts = [
    { label: 'Open', value: incidents.filter((i) => i.status === 'open').length, color: '#3a74f5' },
    { label: 'Resolved', value: incidents.filter((i) => i.status === 'resolved').length, color: '#14c38e' },
    { label: 'Closed', value: incidents.filter((i) => i.status === 'closed').length, color: '#4a5568' },
  ];

  // Live status pill
  const liveLabel = liveStatus?.connected
    ? (liveStatus.latency_ms && liveStatus.latency_ms > 1000 ? 'Slow' : 'Connected')
    : 'Disconnected';
  const liveColor = liveStatus?.connected
    ? (liveStatus.latency_ms && liveStatus.latency_ms > 1000
      ? 'bg-yellow-400'
      : 'bg-green-400')
    : 'bg-red-400';

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-[var(--text)]">Incident Monitoring</h1>
            <p className="text-[13px] text-[var(--muted)]">Real-time incident tracking and SLA compliance</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${liveColor} animate-pulse`} />
            <span className="text-[12px] font-medium text-[var(--muted)]">{liveLabel}</span>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <SearchInput placeholder="Search incidents..." onSearch={handleSearch} value={incidentFilters.search} />
          <FilterChip
            label="Status"
            options={statusOptions}
            value={incidentFilters.status}
            onChange={(v) => handleFilterChange('status', v)}
          />
          <FilterChip
            label="Priority"
            options={priorityOptions}
            value={incidentFilters.priority}
            onChange={(v) => handleFilterChange('priority', v)}
          />
          <FilterChip
            label="Time"
            options={timeOptions}
            value={incidentFilters.timeWindow}
            onChange={(v) => handleFilterChange('timeWindow', v)}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-2 gap-4 max-[1200px]:grid-cols-1">
          <BarChart data={priorityCounts} title="Incidents by Priority" />
          <DonutChart segments={statusCounts} title="Status Breakdown" />
        </div>

        {/* SLA Summary */}
        {slaSummary && (
          <div className="grid grid-cols-2 gap-4 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
            <SlaGauge label="Response Time SLA" value={slaSummary.response_compliance} target={85} />
            <SlaGauge label="Resolution Time SLA" value={slaSummary.resolution_compliance} target={80} />
          </div>
        )}

        {/* Table */}
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-sm)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-[var(--purple)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[var(--line)] bg-[var(--surface-soft)]">
                  {['ID', 'Title', 'Service', 'Priority', 'Status', 'Assignee', 'Opened'].map((h) => (
                    <th key={h} className="px-4 py-3 text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <tr key={inc.id} className="border-b border-[var(--line)] hover:bg-[var(--surface-soft)] transition-colors cursor-pointer">
                    <td className="px-4 py-3 text-[12px] font-mono text-[var(--purple)]">{inc.id}</td>
                    <td className="px-4 py-3 text-[13px] text-[var(--text)] max-w-[200px] truncate">{inc.title}</td>
                    <td className="px-4 py-3 text-[12px] text-[var(--muted)]">{inc.service}</td>
                    <td className="px-4 py-3"><StatusPill status={priorityLabel(inc.severity)} /></td>
                    <td className="px-4 py-3"><StatusPill status={inc.status} /></td>
                    <td className="px-4 py-3 text-[12px] text-[var(--muted)]">{inc.assignee}</td>
                    <td className="px-4 py-3 text-[12px] text-[var(--muted)]">{formatDate(inc.opened_at)}</td>
                  </tr>
                ))}
                {incidents.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-[var(--muted)] text-[13px]">
                      No incidents found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {pagination && pagination.total_pages > 1 && (
          <PaginationControls
            page={pagination.page}
            totalPages={pagination.total_pages}
            onPageChange={handlePageChange}
          />
        )}
      </div>
    </div>
  );
}
