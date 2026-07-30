interface SlaGaugeProps {
  label: string;
  value: number | undefined;
  target: number;
}

export default function SlaGauge({ label, value, target }: SlaGaugeProps) {
  if (value == null) return null;
  const fill = Math.min(value, 100);
  const color =
    value >= target ? 'bg-[var(--green)]' :
    value >= target * 0.8 ? 'bg-[var(--yellow)]' :
    'bg-[var(--red)]';

  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-baseline">
        <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
        <span className="text-sm font-bold text-[var(--text)]">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-[var(--surface-soft)] overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${fill}%` }}
        />
      </div>
    </div>
  );
}
