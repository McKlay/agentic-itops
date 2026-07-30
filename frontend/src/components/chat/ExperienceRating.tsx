import { useChatStore } from '../../store/chatStore';
import type { RatingLevel } from '../../types/api';

const ratings: { level: RatingLevel; icon: string; label: string }[] = [
  { level: 'poor', icon: '☹', label: 'Poor' },
  { level: 'fair', icon: '◔', label: 'Fair' },
  { level: 'good', icon: '◕', label: 'Good' },
  { level: 'great', icon: '☺', label: 'Great' },
  { level: 'excellent', icon: '★', label: 'Excellent' },
];

export default function ExperienceRating() {
  const { activeSessionId, getLatestAssistantMessage, rateMessage } = useChatStore();
  const latestMsg = getLatestAssistantMessage(activeSessionId);

  const handleRate = (level: RatingLevel) => {
    if (latestMsg) {
      rateMessage(activeSessionId, latestMsg.id, level);
    }
  };

  return (
    <div className="flex flex-col items-center gap-1 mt-2 px-1">
      <div className="flex items-center gap-3">
        <span className="text-[11px] text-[var(--muted)]">Rate your experience</span>
        <div className="flex items-center gap-1">
          {ratings.map(({ level, icon }) => (
            <button
              key={level}
              type="button"
              onClick={() => handleRate(level)}
              title={level}
              className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-all ${
                latestMsg?.rating === level
                  ? 'bg-[var(--surface-tint)] border border-[var(--line-strong)] text-[var(--purple)] -translate-y-0.5 shadow-sm'
                  : 'text-[var(--muted)] hover:text-[var(--purple)] hover:bg-[var(--surface-soft)]'
              }`}
            >
              {icon}
            </button>
          ))}
        </div>
      </div>
      <span className="text-[10px] text-[var(--muted)] opacity-60">Rate the latest assistant response.</span>
    </div>
  );
}
