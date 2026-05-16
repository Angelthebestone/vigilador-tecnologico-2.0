import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SessionSummary } from '@/types';
import { deleteSession } from '@/api/endpoints';

interface HistoryStore {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  setSessions: (sessions: SessionSummary[]) => void;
  selectSession: (id: string) => void;
  newSession: () => void;
  removeSession: (id: string) => Promise<void>;
}

export const useHistoryStore = create<HistoryStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,

      setSessions: (sessions) => set({ sessions }),
      selectSession: (id) => set({ activeSessionId: id }),
      newSession: () => set({ activeSessionId: null }),

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
