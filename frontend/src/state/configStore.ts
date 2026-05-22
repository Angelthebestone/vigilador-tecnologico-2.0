import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  WorkstreamConfig,
  WorkstreamHealth,
  PromptTemplate,
  PromptKind,
} from '@/types';
import {
  getWorkstreamConfig,
  patchWorkstreamConfig,
  getWorkstreamHealth,
  getPromptList,
  getPrompt,
  putPrompt,
  restorePrompt,
} from '@/api/evaluation';

interface ConfigState {
  workstreams: WorkstreamConfig;
  prompts: PromptTemplate[];
  selectedPrompt: string | null;
  selectedKind: PromptKind;
  // Cached content per (name, kind) so switching tabs is instant and
  // unsaved edits in one variant aren't lost when the user peeks at another.
  // Key format: `${name}::${kind}`.
  promptContents: Record<string, string>;
  health: WorkstreamHealth | null;
  loading: boolean;
  error: string | null;

  fetchWorkstreams: () => Promise<void>;
  toggleWorkstream: (ws: keyof WorkstreamConfig) => void;
  saveWorkstreams: () => Promise<void>;
  fetchPrompts: () => Promise<void>;
  selectPrompt: (name: string) => Promise<void>;
  selectKind: (kind: PromptKind) => Promise<void>;
  updatePromptContent: (content: string) => void;
  savePrompt: () => Promise<void>;
  restorePrompt: (name: string, kind?: PromptKind) => Promise<void>;
  fetchHealth: () => Promise<void>;
}

function cacheKey(name: string, kind: PromptKind): string {
  return `${name}::${kind}`;
}

export const useConfigStore = create<ConfigState>()(
  persist(
    (set, get) => ({
      workstreams: { wsA: false, wsB: false, wsC: false, wsD: false, wsE: false },
      prompts: [],
      selectedPrompt: null,
      selectedKind: 'system',
      promptContents: {},
      health: null,
      loading: false,
      error: null,

      fetchWorkstreams: async () => {
        try {
          set({ loading: true, error: null });
          const data = await getWorkstreamConfig();
          set({ workstreams: data, loading: false });
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      toggleWorkstream: (ws) => {
        set((state) => ({
          workstreams: {
            ...state.workstreams,
            [ws]: !state.workstreams[ws],
          },
        }));
      },

      saveWorkstreams: async () => {
        try {
          set({ loading: true, error: null });
          const { workstreams } = get();
          await patchWorkstreamConfig(workstreams);
          set({ loading: false });
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      fetchPrompts: async () => {
        try {
          set({ loading: true, error: null });
          const data = await getPromptList();
          set({ prompts: data.templates, loading: false });
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      selectPrompt: async (name) => {
        const kind = get().selectedKind;
        try {
          set({ selectedPrompt: name, loading: true, error: null });
          const data = await getPrompt(name, kind);
          set((state) => ({
            promptContents: {
              ...state.promptContents,
              [cacheKey(name, kind)]: data.content,
            },
            loading: false,
          }));
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      selectKind: async (kind) => {
        const name = get().selectedPrompt;
        set({ selectedKind: kind });
        if (!name) return;
        // Always refetch so the editor reflects current server state for
        // this variant; cached unsaved edits are preserved via promptContents.
        try {
          set({ loading: true, error: null });
          const data = await getPrompt(name, kind);
          set((state) => {
            const key = cacheKey(name, kind);
            // Don't clobber an unsaved edit the user already typed.
            const existing = state.promptContents[key];
            const next = existing !== undefined ? existing : data.content;
            return {
              promptContents: { ...state.promptContents, [key]: next },
              loading: false,
            };
          });
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      updatePromptContent: (content) => {
        const { selectedPrompt, selectedKind } = get();
        if (!selectedPrompt) return;
        set((state) => ({
          promptContents: {
            ...state.promptContents,
            [cacheKey(selectedPrompt, selectedKind)]: content,
          },
        }));
      },

      savePrompt: async () => {
        const { selectedPrompt, selectedKind, promptContents } = get();
        if (!selectedPrompt) return;
        const content = promptContents[cacheKey(selectedPrompt, selectedKind)] ?? '';
        try {
          set({ loading: true, error: null });
          await putPrompt(selectedPrompt, content, selectedKind);
          await get().fetchPrompts();
          set({ loading: false });
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      restorePrompt: async (name, kind) => {
        const effectiveKind = kind ?? get().selectedKind;
        try {
          set({ loading: true, error: null });
          await restorePrompt(name, effectiveKind);
          await get().fetchPrompts();
          if (get().selectedPrompt === name) {
            // Reload only this variant; drop any cached unsaved edits for it.
            const data = await getPrompt(name, effectiveKind);
            set((state) => ({
              promptContents: {
                ...state.promptContents,
                [cacheKey(name, effectiveKind)]: data.content,
              },
              loading: false,
            }));
          } else {
            set({ loading: false });
          }
        } catch (err) {
          set({ error: String(err), loading: false });
        }
      },

      fetchHealth: async () => {
        try {
          const data = await getWorkstreamHealth();
          set({ health: data });
        } catch {
          // health is non-critical
        }
      },
    }),
    {
      name: 'vigilador-config',
      partialize: (state) => ({ workstreams: state.workstreams }),
    },
  ),
);
