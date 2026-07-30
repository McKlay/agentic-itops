interface FilterChipProps {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}

export default function FilterChip({ label, options, value, onChange }: FilterChipProps) {
  const handleClick = () => {
    const currentIndex = options.indexOf(value);
    const nextIndex = (currentIndex + 1) % options.length;
    onChange(options[nextIndex]);
  };

  const isActive = value !== options[0];

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all duration-[var(--transition-fast)] cursor-pointer ${
        isActive
          ? 'bg-[var(--purple)] text-white border-[var(--purple)]'
          : 'bg-[var(--surface)] text-[var(--muted)] border-[var(--line)] hover:border-[var(--purple)] hover:text-[var(--purple)]'
      }`}
    >
      {label}: {value === options[0] ? 'All' : value}
    </button>
  );
}
