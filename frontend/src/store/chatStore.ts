import { create } from 'zustand';
import type { Message, Session, RatingLevel } from '../types/api';

let nextMsgId = 1;

function generateId(): string {
  return `msg_${Date.now()}_${nextMsgId++}`;
}

function generateSessionId(): string {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

interface ChatState {
  sessions: Session[];
  activeSessionId: string;
  conversations: Record<string, Message[]>;
  isLoading: boolean;

  createSession: (title?: string, kind?: string) => string;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  addMessage: (sessionId: string, message: Omit<Message, 'id' | 'created_at'>) => string;
  removeLoadingMessages: (sessionId: string) => void;
  setLoading: (loading: boolean) => void;
  rateMessage: (sessionId: string, messageId: string, rating: RatingLevel) => void;
  clearConversation: (sessionId: string) => void;
  getLatestAssistantMessage: (sessionId: string) => Message | undefined;
}

function loadSessions(): { sessions: Session[]; conversations: Record<string, Message[]>; activeSessionId: string } {
  try {
    const raw = localStorage.getItem('command-center-session-state-v1');
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        sessions: parsed.sessions || [{ id: 'new-chat', title: 'New Chat', meta: 'Ready', kind: 'default' }],
        conversations: parsed.conversations || {},
        activeSessionId: parsed.activeSessionId || 'new-chat',
      };
    }
  } catch { /* ignore */ }
  return {
    sessions: [{ id: 'new-chat', title: 'New Chat', meta: 'Ready', kind: 'default' }],
    conversations: {},
    activeSessionId: 'new-chat',
  };
}

function persistState(state: { sessions: Session[]; conversations: Record<string, Message[]>; activeSessionId: string }) {
  localStorage.setItem('command-center-session-state-v1', JSON.stringify({
    sessions: state.sessions,
    conversations: state.conversations,
    activeSessionId: state.activeSessionId,
  }));
}

const initial = loadSessions();

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: initial.sessions,
  activeSessionId: initial.activeSessionId,
  conversations: initial.conversations,
  isLoading: false,

  createSession: (title = 'New Chat', kind = 'default') => {
    const id = generateSessionId();
    const session: Session = { id, title, meta: 'Ready', kind };
    set((s) => {
      const newState = {
        sessions: [session, ...s.sessions],
        activeSessionId: id,
        conversations: { ...s.conversations, [id]: [] },
      };
      persistState({ ...newState });
      return newState;
    });
    return id;
  },

  switchSession: (id) => {
    set({ activeSessionId: id });
    const s = get();
    persistState({ sessions: s.sessions, conversations: s.conversations, activeSessionId: id });
  },

  deleteSession: (id) => {
    set((s) => {
      const sessions = s.sessions.filter((sess) => sess.id !== id);
      const conversations = { ...s.conversations };
      delete conversations[id];
      const activeSessionId = s.activeSessionId === id
        ? (sessions[0]?.id || 'new-chat')
        : s.activeSessionId;
      if (sessions.length === 0) {
        sessions.push({ id: 'new-chat', title: 'New Chat', meta: 'Ready', kind: 'default' });
      }
      persistState({ sessions, conversations, activeSessionId });
      return { sessions, conversations, activeSessionId };
    });
  },

  renameSession: (id, title) => {
    set((s) => {
      const sessions = s.sessions.map((sess) =>
        sess.id === id ? { ...sess, title } : sess
      );
      persistState({ sessions, conversations: s.conversations, activeSessionId: s.activeSessionId });
      return { sessions };
    });
  },

  addMessage: (sessionId, msg) => {
    const id = generateId();
    const message: Message = {
      ...msg,
      id,
      created_at: new Date().toISOString(),
    };
    set((s) => {
      const current = s.conversations[sessionId] || [];
      const conversations = { ...s.conversations, [sessionId]: [...current, message] };
      persistState({ sessions: s.sessions, conversations, activeSessionId: s.activeSessionId });
      return { conversations };
    });
    return id;
  },

  removeLoadingMessages: (sessionId) => {
    set((s) => {
      const current = s.conversations[sessionId] || [];
      const conversations = {
        ...s.conversations,
        [sessionId]: current.filter((m) => m.kind !== 'loading'),
      };
      return { conversations };
    });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  rateMessage: (sessionId, messageId, rating) => {
    set((s) => {
      const current = s.conversations[sessionId] || [];
      const conversations = {
        ...s.conversations,
        [sessionId]: current.map((m) =>
          m.id === messageId ? { ...m, rating } : m
        ),
      };
      localStorage.setItem(`command-center-rating-${messageId}`, rating);
      persistState({ sessions: s.sessions, conversations, activeSessionId: s.activeSessionId });
      return { conversations };
    });
  },

  clearConversation: (sessionId) => {
    set((s) => {
      const conversations = { ...s.conversations, [sessionId]: [] };
      persistState({ sessions: s.sessions, conversations, activeSessionId: s.activeSessionId });
      return { conversations };
    });
  },

  getLatestAssistantMessage: (sessionId) => {
    const messages = get().conversations[sessionId] || [];
    return [...messages].reverse().find((m) => m.role === 'assistant' && m.kind !== 'loading');
  },
}));
