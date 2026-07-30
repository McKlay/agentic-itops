import type { FeedType } from '../../types/api';
import { IconChevronRight } from './Icons';

interface FeedCardProps {
  type: FeedType;
  agent: string;
  time: string;
  description: string;
}

const accentMap: Record<FeedType, { bg: string; border: string }> = {
  monitoring: { bg: 'bg-[var(--yellow-soft)]', border: 'border-l-[var(--yellow)]' },
  incident: { bg: 'bg-[var(--red-soft)]', border: 'border-l-[var(--red)]' },
  problem: { bg: 'bg-[var(--surface-soft)]', border: 'border-l-[var(--muted)]' },
  orchestration: { bg: 'bg-[var(--purple-soft)]', border: 'border-l-[var(--purple)]' },
};

export default function FeedCard({ type, agent, time, description }: FeedCardProps) {
  const accent = accentMap[type];
  return (
    <div
      className={`rounded-lg ${accent.bg} border border-[var(--line)] border-l-[3px] ${accent.border} transition-all duration-[var(--transition-fast)] hover:shadow-[var(--shadow-sm)] animate-[slideIn_0.3s_ease-out] cursor-pointer group`}
    >
      <div className="px-3 py-2.5">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] font-bold text-[var(--text)] uppercase tracking-wider">
            {agent}
          </span>
          <span className="text-[10px] text-[var(--muted)] tabular-nums">{time}</span>
        </div>
        <div className="flex items-start justify-between gap-2">
          <p className="text-[12px] leading-snug text-[var(--muted)] line-clamp-2">{description}</p>
          <IconChevronRight size={12} className="text-[var(--muted)] opacity-0 group-hover:opacity-60 transition-opacity shrink-0 mt-0.5" />
        </div>
      </div>
    </div>
  );
}
