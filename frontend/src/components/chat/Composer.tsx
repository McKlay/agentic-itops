import { useState } from 'react';
import { useChatStore } from '../../store/chatStore';
import { useUiStore } from '../../store/uiStore';
import { api } from '../../api/client';
import ExperienceRating from './ExperienceRating';
import { IconRefresh, IconSend, IconEraser } from '../shared/Icons';
import type { Artifact, ChatResponse } from '../../types/api';

/** Derive displayable artifacts from an agent's output array and pending approvals. */
function buildArtifacts(response: ChatResponse): Artifact[] {
  const artifacts: Artifact[] = [];

  // Collect all KB outputs and merge into a single source-citation card.
  // Steps and notes are now rendered in the chat bubble (via final_response),
  // so the artifact card only needs to surface cited sources.
  const kbOutputs = (response.agent_outputs ?? []).filter(
    (o) => o.citations && o.citations.length > 0,
  );

  if (kbOutputs.length > 0) {
    const last = kbOutputs[kbOutputs.length - 1];
    // Deduplicate citations across all outputs for this turn
    const allCitations = [...new Set(kbOutputs.flatMap((o) => o.citations ?? []))];
    const allCitationUrls = kbOutputs.reduce<Record<string, string>>(
      (acc, o) => ({ ...acc, ...(o.citation_urls ?? {}) }),
      {},
    );
    artifacts.push({
      type: 'knowledge_result',
      data: {
        agent_id: last.agent_id,
        citations: allCitations,
        citation_urls: allCitationUrls,
        confidence: last.confidence,
      },
    });
  }

  // Surface agent outputs that need approval as an approval card
  for (const output of response.agent_outputs ?? []) {
    if (output.requires_approval) {
      artifacts.push({
        type: 'approval_required',
        data: {
          output_id: output.output_id,
          agent_id: output.agent_id,
          summary: output.summary,
          confidence: output.confidence,
        },
      });
    }
  }

  // Also surface any approval tasks returned by the service layer
  for (const task of response.pending_approvals ?? []) {
    artifacts.push({
      type: 'approval_required',
      data: {
        task_id: task.task_id,
        output_id: task.output_id,
        agent_id: task.agent_id,
        summary: task.summary,
      },
    });
  }

  return artifacts;
}

export default function Composer() {
  const [input, setInput] = useState('');
  const {
    activeSessionId,
    addMessage,
    removeLoadingMessages,
    isLoading,
    setLoading,
    createSession,
    switchSession,
    clearConversation,
  } = useChatStore();
  const { currentView, setView } = useUiStore();

  const handleSubmit = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput('');

    // If on home, switch to conversation view
    if (currentView !== 'conversation') {
      setView('conversation');
    }

    // Add user message
    addMessage(activeSessionId, { role: 'user', content: text });

    // Add loading indicator
    addMessage(activeSessionId, { role: 'assistant', content: '', kind: 'loading' });
    setLoading(true);

    try {
      const response = await api<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          thread_id: activeSessionId,
        }),
      });

      removeLoadingMessages(activeSessionId);

      const artifacts = buildArtifacts(response);
      const hasPendingApprovals = (response.pending_approvals ?? []).length > 0;
      const kind = hasPendingApprovals ? 'approval_required' : 'text';

      addMessage(activeSessionId, {
        role: 'assistant',
        content: response.message || '',
        kind,
        artifacts: artifacts.length > 0 ? artifacts : undefined,
      });
    } catch {
      removeLoadingMessages(activeSessionId);
      addMessage(activeSessionId, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        kind: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = () => {
    const id = createSession();
    switchSession(id);
    setView('conversation');
  };

  const handleClear = () => {
    clearConversation(activeSessionId);
  };

  return (
    <div className="px-6 pb-3 pt-2 bg-gradient-to-t from-[var(--page)] via-[var(--page)] to-transparent">
      <div className="max-w-[700px] mx-auto">
        <div className="flex items-center gap-2 rounded-2xl border border-[var(--line)] bg-[var(--surface)] px-3 py-1.5 shadow-[var(--shadow-md)] focus-within:border-[var(--purple)] focus-within:shadow-[0_4px_16px_rgba(125,72,255,0.12)] transition-all">
          <button
            type="button"
            onClick={handleNewConversation}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--purple)] hover:bg-[var(--surface-tint)] transition-all"
            title="New conversation"
          >
            <IconRefresh size={14} />
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="Message SwiftAssist AI..."
            className="flex-1 bg-transparent text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none py-2"
          />
          <button
            type="button"
            onClick={handleClear}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-tint)] transition-all"
            title="Clear"
          >
            <IconEraser size={13} />
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className="w-8 h-8 rounded-xl flex items-center justify-center bg-[var(--purple)] text-white hover:bg-[var(--purple-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            <IconSend size={14} />
          </button>
        </div>
        <ExperienceRating />
      </div>
    </div>
  );
}
