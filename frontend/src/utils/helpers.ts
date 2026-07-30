/** Formatting & helper utilities */

export function formatDate(value: string | null | undefined): string {
  if (!value) return 'N/A';
  return new Date(value).toLocaleDateString();
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'No activity yet';
  const d = new Date(value);
  const month = d.toLocaleString('default', { month: 'short' });
  return `${month} ${d.getDate()}, ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function formatPercentage(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

export function formatDurationMinutes(totalMinutes: number): string {
  if (totalMinutes < 60) return `${Math.round(totalMinutes)}m`;
  const hours = totalMinutes / 60;
  return hours >= 10 ? `${Math.round(hours)}h` : `${hours.toFixed(1)}h`;
}

export function nowTime(): string {
  return new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function priorityLabel(severity: number): string {
  const labels: Record<number, string> = {
    1: 'P1 - Critical',
    2: 'P2 - High',
    3: 'P3 - Moderate',
    4: 'P4 - Low',
  };
  return labels[severity] || `P${severity}`;
}

export function priorityClass(severity: number): string {
  const classes: Record<number, string> = {
    1: 'text-red-600 bg-red-50',
    2: 'text-orange-600 bg-orange-50',
    3: 'text-blue-600 bg-blue-50',
    4: 'text-green-600 bg-green-50',
  };
  return classes[severity] || '';
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function daysUntil(targetDate: Date): number {
  const now = new Date();
  const diff = targetDate.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export function startOfCurrentWeek(): Date {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? 6 : day - 1;
  const monday = new Date(now);
  monday.setDate(now.getDate() - diff);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

export function profileInitials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || '')
    .join('') || 'U';
}
