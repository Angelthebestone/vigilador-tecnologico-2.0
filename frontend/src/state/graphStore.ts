import { create } from 'zustand';
import type { GraphData } from '@/types';
import { getGraph } from '@/api';

interface GraphStore {
  graphData: GraphData | null;
  selectedNodeId: string | null;
  loading: boolean;
  error: string | null;
  fetchGraph: (sessionId: string) => Promise<void>;
  setSelectedNode: (nodeId: string | null) => void;
  reset: () => void;
}

export const useGraphStore = create<GraphStore>()((set) => ({
  graphData: null,
  selectedNodeId: null,
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

  reset: () =>
    set({
      graphData: null,
      selectedNodeId: null,
      loading: false,
      error: null,
    }),
}));
