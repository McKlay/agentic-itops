import type { Message } from '../../types/api';
import { profileInitials } from '../../utils/helpers';

interface MessageBubbleProps {
  message: Message;
}

/**
 * Render plain-text content that may contain lightweight structure:
 * numbered lists (e.g. "1. Do X"), bullet lines ("• …"), and
 * labelled section headers ("Steps:", "Key Notes:").
 * Paragraphs are separated by blank lines in the source string.
 */
function StructuredContent({ text }: { text: string }) {
  const blocks = text.split(/\n\n+/);
  return (
    <div className="space-y-2.5">
      {blocks.map((block, bi) => {
        const lines = block.split('\n').filter(Boolean);

        // Section header followed by list content (e.g. "Steps:\n1. …")
        if (lines.length > 1 && /^(Steps|Key Notes|Notes):?$/i.test(lines[0])) {
          return (
            <div key={bi}>
              <p className="text-[11px] font-bold text-[var(--muted)] uppercase tracking-wider mb-1.5">
                {lines[0].replace(/:$/, '')}
              </p>
              <StructuredContent text={lines.slice(1).join('\n')} />
            </div>
          );
        }

        // Numbered list — every line starts with "N."
        const isNumbered = lines.every((l) => /^\d+\.\s/.test(l));
        if (isNumbered && lines.length > 0) {
          return (
            <ol key={bi} className="space-y-1.5 list-none pl-0">
              {lines.map((line, li) => {
                const content = line.replace(/^\d+\.\s*/, '');
                return (
                  <li key={li} className="flex items-start gap-2.5 text-sm">
                    <span className="mt-0.5 shrink-0 w-5 h-5 rounded-full bg-[var(--purple)] text-white text-[10px] font-bold flex items-center justify-center">
                      {li + 1}
                    </span>
                    <span className="leading-relaxed text-[var(--text)]">{content}</span>
                  </li>
                );
              })}
            </ol>
          );
        }

        // Bullet list — every line starts with "•" or "-"
        const isBullet = lines.every((l) => /^[•\-]\s/.test(l));
        if (isBullet && lines.length > 0) {
          return (
            <ul key={bi} className="space-y-1 pl-1 list-none">
              {lines.map((line, li) => {
                const content = line.replace(/^[•\-]\s*/, '');
                return (
                  <li key={li} className="flex items-start gap-2 text-sm">
                    <span className="mt-2 shrink-0 w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span className="leading-relaxed text-[var(--text)]">{content}</span>
                  </li>
                );
              })}
            </ul>
          );
        }

        // Plain paragraph
        return (
          <p key={bi} className="text-sm leading-relaxed text-[var(--text)] whitespace-pre-wrap">
            {block}
          </p>
        );
      })}
    </div>
  );
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isLoading = message.kind === 'loading';

  if (isLoading) {
    return (
      <div className="flex items-start gap-3 animate-[slideIn_0.3s_ease-out]">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--purple)] to-[#a855f7] flex items-center justify-center text-white text-[10px] font-bold shrink-0 shadow-sm">
          S
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-[var(--purple)]">SwiftAssist AI</span>
          <div className="rounded-2xl rounded-tl-lg bg-[var(--surface)] border border-[var(--line)] px-4 py-3 shadow-[var(--shadow-sm)]">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-[var(--purple)] border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-[var(--muted)]">Thinking...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end animate-[slideIn_0.3s_ease-out]">
        <div className="flex flex-col items-end gap-1 max-w-[70%]">
          <div className="rounded-2xl rounded-tr-lg bg-[var(--blue-soft)] px-4 py-3 shadow-[var(--shadow-sm)]">
            <p className="text-sm leading-relaxed text-[var(--text)] whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
          <span className="text-[11px] text-[var(--muted)]">
            {new Date(message.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
          </span>
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#64748b] to-[#475569] flex items-center justify-center text-white text-[10px] font-bold shrink-0 shadow-sm">
          {profileInitials('John Doe')}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex items-start gap-3 animate-[slideIn_0.3s_ease-out]">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--purple)] to-[#a855f7] flex items-center justify-center text-white text-[10px] font-bold shrink-0 shadow-sm">
        S
      </div>
      <div className="flex flex-col gap-1 max-w-[70%]">
        <span className="text-[11px] font-semibold text-[var(--purple)]">SwiftAssist AI</span>
        <div className="rounded-2xl rounded-tl-lg bg-[var(--surface)] border border-[var(--line)] px-4 py-3 shadow-[var(--shadow-sm)]">
          <StructuredContent text={message.content} />
        </div>
        <span className="text-[11px] text-[var(--muted)]">
          SwiftAssist AI · {new Date(message.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
        </span>
        {message.rating && (
          <span className="text-[11px] text-[var(--muted)] italic">
            Rated: {message.rating}
          </span>
        )}
      </div>
    </div>
  );
}
