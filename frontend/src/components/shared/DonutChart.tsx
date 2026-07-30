interface DonutChartProps {
  segments: { label: string; value: number; color: string }[];
  title: string;
}

export default function DonutChart({ segments, title }: DonutChartProps) {
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1;
  let accumulated = 0;
  const gradientParts = segments.map((s) => {
    const start = (accumulated / total) * 360;
    accumulated += s.value;
    const end = (accumulated / total) * 360;
    return `${s.color} ${start}deg ${end}deg`;
  });

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]">
      <h3 className="text-sm font-semibold text-[var(--text)] mb-4">{title}</h3>
      <div className="flex items-center gap-6">
        <div
          className="w-28 h-28 rounded-full shrink-0 relative"
          style={{ background: `conic-gradient(${gradientParts.join(', ')})` }}
        >
          <div className="absolute inset-3 rounded-full bg-[var(--surface)]" />
        </div>
        <div className="flex flex-col gap-2">
          {segments.map((s) => (
            <div key={s.label} className="flex items-center gap-2 text-xs">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: s.color }}
              />
              <span className="text-[var(--muted)]">{s.label}</span>
              <span className="font-semibold text-[var(--text)] ml-auto">{s.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
