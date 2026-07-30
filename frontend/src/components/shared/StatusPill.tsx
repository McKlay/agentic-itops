interface StatusPillProps {
  status: string;
  variant?: 'status' | 'impact';
}

const statusColors: Record<string, string> = {
  low: 'bg-[var(--green-soft)] text-[#16a26d]',
  resolved: 'bg-[var(--green-soft)] text-[#16a26d]',
  closed: 'bg-gray-100 text-gray-600',
  moderate: 'bg-[var(--blue-soft)] text-[#4676f6]',
  open: 'bg-[var(--blue-soft)] text-[#4676f6]',
  'in progress': 'bg-[var(--blue-soft)] text-[#4676f6]',
  approved: 'bg-[var(--lavender-soft)] text-[#8b2cf4]',
  implemented: 'bg-[var(--lavender-soft)] text-[#8b2cf4]',
  pending: 'bg-[var(--yellow-soft)] text-[#b8860b]',
  draft: 'bg-[var(--yellow-soft)] text-[#b8860b]',
  review: 'bg-[var(--purple-soft)] text-[var(--purple)]',
  rejected: 'bg-[var(--red-soft)] text-[#d94343]',
};

const impactColors: Record<string, string> = {
  clean: 'bg-[var(--green-soft)] text-[#20a977]',
  incident: 'bg-[var(--red-soft)] text-[#ea5d5d]',
};

export default function StatusPill({ status, variant = 'status' }: StatusPillProps) {
  const normalized = status.toLowerCase();
  const colorMap = variant === 'impact' ? impactColors : statusColors;
  const colors = colorMap[normalized] || 'bg-[var(--surface-soft)] text-[var(--muted)]';

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase ${colors}`}
    >
      {status}
    </span>
  );
}
