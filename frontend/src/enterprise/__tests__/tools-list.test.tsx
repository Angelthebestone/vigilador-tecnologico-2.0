import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useToolsStore } from '../state/toolsStore';

vi.mock('../api/enterpriseClient', () => ({
  getTools: vi.fn(),
  getToken: vi.fn().mockReturnValue('tok'),
}));

import { getTools } from '../api/enterpriseClient';
import { ToolsListPage } from '../tools/ToolsListPage';

const FAKE_TOOLS = [
  { id: 'tool-1', description: 'Desc 1', domains: ['d1.com'], requiresAuth: false, costTier: 'free', status: 'UP' },
  { id: 'tool-2', description: 'Desc 2', domains: ['d2.com'], requiresAuth: true, costTier: 'paid', status: 'DOWN' },
  { id: 'tool-3', description: 'Desc 3', domains: ['d3.com', 'd4.com'], requiresAuth: false, costTier: 'free', status: 'UNCONFIGURED' },
  { id: 'tool-4', description: 'Desc 4', domains: ['d5.com'], requiresAuth: false, costTier: 'free', status: 'UP' },
  { id: 'tool-5', description: 'Desc 5', domains: ['d6.com'], requiresAuth: true, costTier: 'paid', status: 'DOWN' },
];

beforeEach(() => {
  vi.clearAllMocks();
  useToolsStore.setState({ tools: [], lastFetch: null, loading: false });
  (getTools as ReturnType<typeof vi.fn>).mockResolvedValue(FAKE_TOOLS);
});

describe('T053 – ToolsListPage', () => {
  it('renders 5 tool rows after fetch', async () => {
    render(<ToolsListPage />);

    await waitFor(() => {
      for (const t of FAKE_TOOLS) {
        expect(screen.getByText(t.id)).toBeInTheDocument();
      }
    });
  });

  it('shows correct status badges: UP=success, DOWN=error, UNCONFIGURED=info', async () => {
    render(<ToolsListPage />);

    await waitFor(() => expect(screen.getByText('tool-1')).toBeInTheDocument());

    const upBadges = screen.getAllByText('UP');
    upBadges.forEach((el) => expect(el.closest('.badge')).toHaveClass('badge--success'));

    const downBadges = screen.getAllByText('DOWN');
    downBadges.forEach((el) => expect(el.closest('.badge')).toHaveClass('badge--error'));

    const unconfigured = screen.getByText('UNCONFIGURED');
    expect(unconfigured.closest('.badge')).toHaveClass('badge--info');
  });

  it('displays joined domains', async () => {
    render(<ToolsListPage />);

    await waitFor(() => expect(screen.getByText('d3.com, d4.com')).toBeInTheDocument());
  });

  it('calls refresh on mount (getTools called)', async () => {
    render(<ToolsListPage />);

    await waitFor(() => expect(getTools).toHaveBeenCalledWith('card'));
  });

  it('shows empty message when no tools', async () => {
    (getTools as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<ToolsListPage />);

    await waitFor(() => expect(screen.getByText(/no hay herramientas/i)).toBeInTheDocument());
  });
});
