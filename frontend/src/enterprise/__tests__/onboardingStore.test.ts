// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { localStorageMock } = vi.hoisted(() => {
  const store: Record<string, string> = {};
  const localStorageMock = {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
  Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true, configurable: true });
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true, configurable: true });
  }
  return { localStorageMock };
});

vi.mock('../api/enterpriseClient', () => ({
  saveCompany: vi.fn().mockResolvedValue(undefined),
  saveLlmProvider: vi.fn().mockResolvedValue({ status: 'ok', provider: 'openai' }),
}));

import { useOnboardingStore } from '../state/onboardingStore';

beforeEach(() => {
  localStorageMock.clear();
  useOnboardingStore.setState({
    companyProfile: null,
    llmProvider: null,
    currentStep: 1,
  });
});

describe('initial state', () => {
  it('has null companyProfile, null llmProvider, step 1', () => {
    const s = useOnboardingStore.getState();
    expect(s.companyProfile).toBeNull();
    expect(s.llmProvider).toBeNull();
    expect(s.currentStep).toBe(1);
  });
});

describe('setStep', () => {
  it('changes currentStep', () => {
    useOnboardingStore.getState().setStep(2);
    expect(useOnboardingStore.getState().currentStep).toBe(2);
  });
});

describe('saveStep1', () => {
  it('persists companyProfile and advances to step 2', async () => {
    const profile = { name: 'Acme', sector: 'tech' };
    await useOnboardingStore.getState().saveStep1(profile);
    const s = useOnboardingStore.getState();
    expect(s.companyProfile).toEqual(profile);
    expect(s.currentStep).toBe(2);
  });
});

describe('saveStep2', () => {
  it('persists llmProvider', async () => {
    await useOnboardingStore.getState().saveStep2('openai', 'key', 'gpt-4');
    const s = useOnboardingStore.getState();
    expect(s.llmProvider).toEqual({ provider: 'openai', model: 'gpt-4' });
  });
});

describe('loadFromBackend', () => {
  it('resolves without error (placeholder)', async () => {
    await expect(useOnboardingStore.getState().loadFromBackend()).resolves.toBeUndefined();
  });
});
