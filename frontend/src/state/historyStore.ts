import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SessionSummary } from '@/types';

interface HistoryStore {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  setSessions: (sessions: SessionSummary[]) => void;
  selectSession: (id: string) => void;
  newSession: () => void;
}

export const useHistoryStore = create<HistoryStore>()(
  persist(
    (set) => ({
      sessions: [],
      activeSessionId: null,

      setSessions: (sessions) => set({ sessions }),
      selectSession: (id) => set({ activeSessionId: id }),
      newSession: () => set({ activeSessionId: null }),
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
