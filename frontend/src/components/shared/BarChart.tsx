interface BarChartProps {
  data: { label: string; value: number; color?: string }[];
  title: string;
}

const defaultColors = ['#3a74f5', '#14c38e', '#f0ad35', '#d54f4f', '#b241ff', '#4a5568'];

export default function BarChart({ data, title }: BarChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]">
      <h3 className="text-sm font-semibold text-[var(--text)] mb-4">{title}</h3>
      <div className="flex items-end gap-3 h-36">
        {data.map((item, i) => (
          <div key={item.label} className="flex-1 flex flex-col items-center gap-2">
            <span className="text-xs font-semibold text-[var(--text)]">{item.value}</span>
            <div
              className="w-full rounded-t-md transition-all duration-300"
              style={{
                height: `${(item.value / maxValue) * 100}%`,
                minHeight: '4px',
                backgroundColor: item.color || defaultColors[i % defaultColors.length],
              }}
            />
            <span className="text-[10px] text-[var(--muted)] text-center leading-tight">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
