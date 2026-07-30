import { useEffect } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';

interface ServiceNode {
  name: string;
  healthPct: number;
  incidentCount: number;
}

interface DomainGroup {
  domain: string;
  services: ServiceNode[];
}

function buildGroups(dashboard: ReturnType<typeof useDashboardStore.getState>['dashboard']): DomainGroup[] {
  if (!dashboard) return [];

  const domainMap = new Map<string, ServiceNode[]>();

  // Build from incidents
  for (const inc of dashboard.incidents) {
    const domain = inc.domain || 'Other';
    if (!domainMap.has(domain)) domainMap.set(domain, []);
    const services = domainMap.get(domain)!;
    let node = services.find((s) => s.name === inc.service);
    if (!node) {
      node = { name: inc.service, healthPct: 100, incidentCount: 0 };
      services.push(node);
    }
    node.incidentCount++;
    // Degrade health by incident count
    node.healthPct = Math.max(0, 100 - node.incidentCount * 10);
  }

  // Add telemetry signals
  for (const sig of dashboard.telemetry_signals) {
    for (const [, services] of domainMap) {
      const node = services.find((s) => s.name === sig.service);
      if (node && sig.severity === 'critical') {
        node.healthPct = Math.max(0, node.healthPct - 15);
      }
    }
  }

  return Array.from(domainMap.entries()).map(([domain, services]) => ({ domain, services }));
}

export default function ObservabilityPage() {
  const { dashboard, fetchDashboard } = useDashboardStore();

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const groups = buildGroups(dashboard);

  const totalServices = groups.reduce((n, g) => n + g.services.length, 0);
  const healthyServices = groups.reduce((n, g) => n + g.services.filter((s) => s.healthPct >= 80).length, 0);
  const degradedServices = groups.reduce((n, g) => n + g.services.filter((s) => s.healthPct >= 50 && s.healthPct < 80).length, 0);
  const criticalServices = groups.reduce((n, g) => n + g.services.filter((s) => s.healthPct < 50).length, 0);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-5xl mx-auto space-y-5">
        {/* Page header */}
        <div>
          <h1 className="text-xl font-bold text-[var(--text)]">Observability</h1>
          <p className="text-[13px] text-[var(--muted)]">Service health and monitoring grouped by domain</p>
        </div>

        {/* Summary strip */}
        {totalServices > 0 && (
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 flex items-center gap-3 shadow-[var(--shadow-sm)]">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--green)] shrink-0" />
              <div>
                <div className="text-lg font-bold text-[var(--text)]">{healthyServices}</div>
                <div className="text-[11px] text-[var(--muted)] font-medium uppercase tracking-wide">Healthy</div>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 flex items-center gap-3 shadow-[var(--shadow-sm)]">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--yellow)] shrink-0" />
              <div>
                <div className="text-lg font-bold text-[var(--text)]">{degradedServices}</div>
                <div className="text-[11px] text-[var(--muted)] font-medium uppercase tracking-wide">Degraded</div>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 flex items-center gap-3 shadow-[var(--shadow-sm)]">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--red)] shrink-0" />
              <div>
                <div className="text-lg font-bold text-[var(--text)]">{criticalServices}</div>
                <div className="text-[11px] text-[var(--muted)] font-medium uppercase tracking-wide">Critical</div>
              </div>
            </div>
          </div>
        )}

        {/* Domain groups */}
        {groups.length > 0 ? (
          <div className="space-y-4">
            {groups.map((group) => (
              <div key={group.domain} className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]">
                {/* Domain header */}
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-[var(--text)] flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--purple)]" />
                    {group.domain}
                  </h3>
                  <span className="text-[11px] text-[var(--muted)] font-medium">
                    {group.services.length} service{group.services.length !== 1 ? 's' : ''}
                  </span>
                </div>
                {/* Services 2-column grid */}
                <div className="grid grid-cols-2 gap-x-6 gap-y-3.5 max-[700px]:grid-cols-1">
                  {group.services.map((svc) => {
                    const colorClass = svc.healthPct >= 80 ? 'text-[var(--green)]' : svc.healthPct >= 50 ? 'text-[var(--yellow)]' : 'text-[var(--red)]';
                    const barClass = svc.healthPct >= 80 ? 'bg-[var(--green)]' : svc.healthPct >= 50 ? 'bg-[var(--yellow)]' : 'bg-[var(--red)]';
                    return (
                      <div key={svc.name}>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[12px] font-medium text-[var(--text)] truncate max-w-[60%]">{svc.name}</span>
                          <div className="flex items-center gap-2 shrink-0">
                            {svc.incidentCount > 0 && (
                              <span className="text-[10px] font-semibold text-[var(--red)] bg-[var(--red-soft)] px-1.5 py-0.5 rounded-full">
                                {svc.incidentCount} inc
                              </span>
                            )}
                            <span className={`text-[11px] font-bold ${colorClass}`}>{svc.healthPct}%</span>
                          </div>
                        </div>
                        <div className="h-1.5 rounded-full bg-[var(--surface-soft)] overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${barClass}`}
                            style={{ width: `${svc.healthPct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] py-16 text-center shadow-[var(--shadow-sm)]">
            <p className="text-[13px] font-medium text-[var(--text)] mb-1">No observability data available</p>
            <p className="text-[12px] text-[var(--muted)]">Connect your monitoring source to start seeing service health.</p>
          </div>
        )}
      </div>
    </div>
  );
}
