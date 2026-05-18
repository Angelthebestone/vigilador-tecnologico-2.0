import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SessionStatus, SessionSummary } from '@/types';
import { deleteSession } from '@/api/endpoints';

interface HistoryStore {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  setSessions: (sessions: SessionSummary[]) => void;
  selectSession: (id: string) => void;
  newSession: () => void;
  removeSession: (id: string) => Promise<void>;
  addSession: (id: string, query: string, status: SessionStatus) => void;
}

export const useHistoryStore = create<HistoryStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,

      setSessions: (sessions) => set({ sessions }),
      selectSession: (id) => set({ activeSessionId: id }),
      newSession: () => set({ activeSessionId: null }),

      addSession: (id, query, status) =>
        set((state) => {
          if (state.sessions.some((s) => s.id === id)) return state;
          return {
            sessions: [
              ...state.sessions,
              { id, query, date: new Date().toISOString(), status },
            ],
          };
        }),

      removeSession: async (id) => {
        await deleteSession(id);
        const { sessions, activeSessionId } = get();
        set({
          sessions: sessions.filter((s) => s.id !== id),
          activeSessionId: activeSessionId === id ? null : activeSessionId,
        });
      },
    }),
    {
      name: 'vigilador-history',
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
      }),
    }
  )
);
