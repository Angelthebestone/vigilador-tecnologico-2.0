import { create } from 'zustand';
import type { ToolCard } from '../types';
import { getTools } from '../api/enterpriseClient';

interface ToolsState {
  tools: ToolCard[];
  lastFetch: number | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

export const useToolsStore = create<ToolsState>()((set) => ({
  tools: [],
  lastFetch: null,
  loading: false,

  refresh: async () => {
    set({ loading: true });
    try {
      const tools = await getTools('card');
      set({ tools, lastFetch: Date.now(), loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
