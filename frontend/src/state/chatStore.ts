import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage } from '@/types';

interface ChatStore {
  messages: ChatMessage[];
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  addClarification: (questions: Array<{ id: string; text: string }>) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (msg) =>
        set((state) => ({
          messages: [
            ...state.messages,
            { ...msg, id: crypto.randomUUID(), timestamp: new Date().toISOString() } as ChatMessage,
          ],
        })),
      addClarification: (questions) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              id: crypto.randomUUID(),
              type: 'clarification',
              role: 'assistant',
              content: '',
              timestamp: new Date().toISOString(),
              metadata: { questions },
            } as ChatMessage,
          ],
        })),
      clearMessages: () => set({ messages: [] }),
    }),
    {
      name: 'vigilador-chat',
      partialize: (state) => ({ messages: state.messages }),
    }
  )
);
