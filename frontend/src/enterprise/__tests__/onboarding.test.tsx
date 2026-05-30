import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { create } from 'zustand';

// Mock enterpriseClient
const mockLogin = vi.fn().mockResolvedValue({ token: 'tok123', username: 'admin' });
const mockSaveCompany = vi.fn().mockResolvedValue(undefined);
const mockSaveLlmProvider = vi.fn().mockResolvedValue({ status: 'ok', provider: 'xiaomimimo' });
const mockTestLlm = vi.fn().mockResolvedValue({ status: 'ok', model: 'mimo-7b', latencyMs: 120 });

vi.mock('../api/enterpriseClient', () => ({
  login: (...args: unknown[]) => mockLogin(...args),
  saveCompany: (...args: unknown[]) => mockSaveCompany(...args),
  saveLlmProvider: (...args: unknown[]) => mockSaveLlmProvider(...args),
  testLlm: (...args: unknown[]) => mockTestLlm(...args),
  setToken: vi.fn(),
  getToken: vi.fn().mockReturnValue('tok123'),
  clearToken: vi.fn(),
}));

// Create a non-persist version of the store for testing
const createStore = () => create<{
  companyProfile: { name: string; sector?: string; country?: string; department?: string; municipality?: string; timezone?: string } | null;
  llmProvider: { provider: string; model?: string } | null;
  currentStep: 1 | 2;
  saveStep1: (profile: { name: string }) => Promise<void>;
  saveStep2: (provider: string, apiKey: string, model?: string) => Promise<void>;
  loadFromBackend: () => Promise<void>;
  setStep: (n: 1 | 2) => void;
}>((set) => ({
  companyProfile: null,
  llmProvider: null,
  currentStep: 1,
  saveStep1: async (profile) => {
    await mockSaveCompany(profile);
    set({ companyProfile: profile, currentStep: 2 });
  },
  saveStep2: async (provider, apiKey, model) => {
    await mockSaveLlmProvider(provider, apiKey, model);
    set({ llmProvider: { provider, model } });
  },
  loadFromBackend: async () => {},
  setStep: (n) => set({ currentStep: n }),
}));

let mockStore = createStore();

vi.mock('../state/onboardingStore', () => ({
  useOnboardingStore: (...args: unknown[]) => mockStore(...(args as [])),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

import { LoginPage } from '../auth/LoginPage';
import { OnboardingFlow } from '../onboarding/OnboardingFlow';

beforeEach(() => {
  vi.clearAllMocks();
  mockStore = createStore();
});

describe('T052 – Onboarding flow', () => {
  it('LoginPage: login success navigates to onboarding', async () => {
    render(<MemoryRouter><LoginPage /></MemoryRouter>);

    fireEvent.change(screen.getByLabelText(/usuario/i), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: 'pass123' } });
    fireEvent.click(screen.getByRole('button', { name: /ingresar/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/enterprise/onboarding'));
  });

  it('LoginPage: shows error on failure', async () => {
    mockLogin.mockRejectedValueOnce(new Error('fail'));

    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText(/usuario/i), { target: { value: 'bad' } });
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: 'bad' } });
    fireEvent.click(screen.getByRole('button', { name: /ingresar/i }));

    await waitFor(() => expect(screen.getByText('Credenciales inválidas')).toBeInTheDocument());
  });

  it('OnboardingFlow Step1 -> Step2 full flow', async () => {
    render(<MemoryRouter><OnboardingFlow /></MemoryRouter>);

    expect(screen.getByText('Paso 1: Empresa')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'Acme Corp' } });
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));

    await waitFor(() => expect(screen.getByText('Paso 2: Proveedor LLM')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/api key/i), { target: { value: 'sk-test-123' } });
    fireEvent.click(screen.getByRole('button', { name: /guardar y continuar/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/enterprise/tools'));
  });

  it('Step1 validation: name too short shows error', async () => {
    render(<MemoryRouter><OnboardingFlow /></MemoryRouter>);

    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'A' } });
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));

    await waitFor(() => expect(screen.getByText(/mín. 2 caracteres/i)).toBeInTheDocument());
  });

  it('Persistence: after Step1 save, store has currentStep=2 and companyProfile', async () => {
    render(<MemoryRouter><OnboardingFlow /></MemoryRouter>);

    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'Acme Corp' } });
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));

    await waitFor(() => expect(screen.getByText('Paso 2: Proveedor LLM')).toBeInTheDocument());

    const state = mockStore.getState();
    expect(state.currentStep).toBe(2);
    expect(state.companyProfile).toEqual(expect.objectContaining({ name: 'Acme Corp' }));
  });

  it('Step2: test connectivity shows model and latency', async () => {
    act(() => mockStore.setState({ currentStep: 2, companyProfile: { name: 'Test' } }));

    render(<MemoryRouter><OnboardingFlow /></MemoryRouter>);

    fireEvent.click(screen.getByRole('button', { name: /probar conectividad/i }));

    await waitFor(() => {
      expect(screen.getByText(/mimo-7b/)).toBeInTheDocument();
      expect(screen.getByText(/120ms/)).toBeInTheDocument();
    });
  });

  it('Step2: toggle show/hide key and change provider', async () => {
    act(() => mockStore.setState({ currentStep: 2, companyProfile: { name: 'Test' } }));

    render(<MemoryRouter><OnboardingFlow /></MemoryRouter>);

    // Toggle show key
    fireEvent.click(screen.getByRole('button', { name: /mostrar/i }));
    expect(screen.getByRole('button', { name: /ocultar/i })).toBeInTheDocument();

    // Change provider
    fireEvent.change(screen.getByDisplayValue('Xiaomimimo'), { target: { value: 'minimax' } });
  });

  it('Step2: test connectivity error path', async () => {
    mockTestLlm.mockRejectedValueOnce(new Error('network'));
    act(() => mockStore.setState({ currentStep: 2, companyProfile: { name: 'Test' } }));

    render(<MemoryRouter><OnboardingFlow /></MemoryRouter>);

    fireEvent.click(screen.getByRole('button', { name: /probar conectividad/i }));

    await waitFor(() => {
      expect(screen.getByText(/error de conectividad/i)).toBeInTheDocument();
    });
  });
});
