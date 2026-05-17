import { create } from 'zustand';
import type { GraphData } from '@/types';
import { getGraph } from '@/api';

interface GraphStore {
  graphData: GraphData | null;
  selectedNodeId: string | null;
  showSources: boolean;
  loading: boolean;
  error: string | null;
  fetchGraph: (sessionId: string) => Promise<void>;
  setSelectedNode: (nodeId: string | null) => void;
  toggleSources: () => void;
  reset: () => void;
}

export const useGraphStore = create<GraphStore>()((set) => ({
  graphData: null,
  selectedNodeId: null,
  showSources: false,
  loading: false,
  error: null,

  fetchGraph: async (sessionId) => {
    set({ loading: true, error: null });
    try {
      const data = await getGraph(sessionId);
      set({ graphData: data, loading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Error desconocido',
        loading: false,
      });
    }
  },

  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),

  toggleSources: () => set((s) => ({ showSources: !s.showSources })),

  reset: () =>
    set({
      graphData: null,
      selectedNodeId: null,
      showSources: false,
      loading: false,
      error: null,
    }),
}));
