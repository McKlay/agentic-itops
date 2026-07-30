interface MetricTileProps {
  label: string;
  value: string | number;
  accent?: string;
}

export default function MetricTile({ label, value, accent }: MetricTileProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-0.5 rounded-lg bg-[var(--surface-soft)] px-2 py-2 text-center">
      <strong className={`text-base font-bold tabular-nums ${accent || 'text-[var(--text)]'}`}>{value}</strong>
      <span className="text-[9px] font-semibold text-[var(--muted)] uppercase tracking-wider leading-tight">
        {label}
      </span>
    </div>
  );
}
