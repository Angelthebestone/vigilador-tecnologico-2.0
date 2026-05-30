import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CompanyProfile, LlmProviderState } from '../types';
import { saveCompany, saveLlmProvider } from '../api/enterpriseClient';

interface OnboardingState {
  companyProfile: CompanyProfile | null;
  llmProvider: LlmProviderState | null;
  currentStep: 1 | 2;
  saveStep1: (profile: CompanyProfile) => Promise<void>;
  saveStep2: (provider: string, apiKey: string, model?: string) => Promise<void>;
  loadFromBackend: () => Promise<void>;
  setStep: (n: 1 | 2) => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      companyProfile: null,
      llmProvider: null,
      currentStep: 1,

      saveStep1: async (profile) => {
        await saveCompany(profile);
        set({ companyProfile: profile, currentStep: 2 });
      },

      saveStep2: async (provider, apiKey, model) => {
        await saveLlmProvider(provider, apiKey, model);
        set({ llmProvider: { provider, model } });
      },

      loadFromBackend: async () => {
        // placeholder – will be implemented when backend supports GET
      },

      setStep: (n) => set({ currentStep: n }),
    }),
    {
      name: 'vigilador-onboarding',
      partialize: (state) => ({
        companyProfile: state.companyProfile,
        currentStep: state.currentStep,
      }),
    },
  ),
);
