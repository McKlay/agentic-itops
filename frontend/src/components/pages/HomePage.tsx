import { useUiStore } from '../../store/uiStore';
import { useChatStore } from '../../store/chatStore';
import { IconClipboardList, IconTarget, IconBarChart, IconBookOpen } from '../shared/Icons';
import type { ReactNode } from 'react';

const quickActions: { label: string; color: string; icon: ReactNode; action: string }[] = [
  {
    label: 'What incidents were opened this week?',
    color: 'bg-[var(--blue-soft)]',
    icon: <IconClipboardList size={18} className="text-[#3b82f6]" />,
    action: 'incidents',
  },
  {
    label: 'What problems are due this week?',
    color: 'bg-[var(--pink-soft)]',
    icon: <IconTarget size={18} className="text-[#e54d4d]" />,
    action: 'problems',
  },
  {
    label: 'Generate an RCA/CAP report for the top problem',
    color: 'bg-[var(--lavender-soft)]',
    icon: <IconBarChart size={18} className="text-[var(--purple)]" />,
    action: 'rca',
  },
  {
    label: 'Search the knowledge base for troubleshooting steps',
    color: 'bg-[var(--mint-soft)]',
    icon: <IconBookOpen size={18} className="text-[#18a957]" />,
    action: 'knowledge',
  },
];

export default function HomePage() {
  const setView = useUiStore((s) => s.setView);
  const { addMessage, activeSessionId } = useChatStore();

  const handleAction = (action: string, label: string) => {
    if (action === 'incidents') {
      setView('incidents');
    } else if (action === 'problems') {
      setView('problems');
    } else {
      addMessage(activeSessionId, { role: 'user', content: label });
      setView('conversation');
    }
  };

  return (
    <div className="flex flex-col items-center px-6 pt-10 pb-4">
      {/* Hero */}
      <div className="flex flex-col items-center text-center mb-8">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[var(--purple)] to-[#a855f7] flex items-center justify-center mb-5 shadow-lg">
          <span className="text-xl text-white font-bold">S</span>
        </div>
        <h1 className="text-xl font-bold text-[var(--text)] mb-0.5">Hello! I'm SwiftAssist AI</h1>
        <h2 className="text-base font-medium text-[var(--muted)] mb-2">How can I help you today?</h2>
        <p className="text-[13px] text-[var(--muted)] max-w-sm leading-relaxed">
          Operate incidents, problems, knowledge, and governed change through approval-first AI workflows.
        </p>
      </div>

      {/* Quick Actions Grid */}
      <div className="grid grid-cols-2 gap-2.5 max-w-md w-full">
        {quickActions.map((card) => (
          <button
            key={card.action}
            type="button"
            onClick={() => handleAction(card.action, card.label)}
            className={`${card.color} rounded-xl px-3.5 py-3.5 text-left cursor-pointer group transition-all duration-200 hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5 border border-transparent hover:border-[var(--line)]`}
          >
            <span className="flex items-start gap-2">
              <span className="shrink-0 mt-0.5">{card.icon}</span>
              <span className="text-[12px] font-semibold text-[var(--text)] leading-snug">
                {card.label}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
