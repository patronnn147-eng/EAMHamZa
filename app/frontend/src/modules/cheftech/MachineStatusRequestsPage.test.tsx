import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

import MachineStatusRequestsPage from './MachineStatusRequestsPage';

function mkItem(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    machine_id: 10,
    machine_name: 'Presse A',
    from_status: 'OPERATIONNELLE',
    to_status: 'EN_PANNE',
    requested_by: 5,
    requested_by_name: 'Jean Tech',
    requested_at: '2026-07-24T10:00:00Z',
    source_intervention_id: null,
    ...overrides,
  };
}

function mockFetchSequence(...responses: Array<{ ok: boolean; json?: () => Promise<unknown> }>) {
  const fn = vi.fn();
  for (const r of responses) fn.mockResolvedValueOnce(r);
  globalThis.fetch = fn as typeof fetch;
  return fn;
}

beforeEach(() => {
  mockToast.mockReset();
  localStorage.setItem('access_token', 'test-token');
});

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('MachineStatusRequestsPage', () => {
  it('shows the empty state when there are no pending requests', async () => {
    mockFetchSequence({ ok: true, json: async () => ({ items: [] }) });
    render(<MachineStatusRequestsPage />);
    expect(await screen.findByText('Aucune demande en attente')).toBeTruthy();
    expect(screen.getByText('0 en attente')).toBeTruthy();
  });

  it('renders pending requests with translated status labels', async () => {
    mockFetchSequence({ ok: true, json: async () => ({ items: [mkItem()] }) });
    render(<MachineStatusRequestsPage />);
    expect(await screen.findByText(/Presse A/)).toBeTruthy();
    expect(screen.getByText('Jean Tech')).toBeTruthy();
    expect(screen.getByText('Opérationnelle')).toBeTruthy();
    expect(screen.getByText('En Panne')).toBeTruthy();
  });

  it('falls back to a user id label when requested_by_name is null', async () => {
    mockFetchSequence({
      ok: true,
      json: async () => ({ items: [mkItem({ requested_by_name: null, requested_by: 7 })] }),
    });
    render(<MachineStatusRequestsPage />);
    expect(await screen.findByText('Utilisateur #7')).toBeTruthy();
  });

  it('shows the empty state when the fetch fails (non-ok response)', async () => {
    mockFetchSequence({ ok: false });
    render(<MachineStatusRequestsPage />);
    expect(await screen.findByText('Aucune demande en attente')).toBeTruthy();
  });

  it('shows the empty state when fetch throws', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network')) as typeof fetch;
    render(<MachineStatusRequestsPage />);
    expect(await screen.findByText('Aucune demande en attente')).toBeTruthy();
  });

  it('approves a request and removes it from the list', async () => {
    mockFetchSequence(
      { ok: true, json: async () => ({ items: [mkItem()] }) },
      { ok: true }
    );
    render(<MachineStatusRequestsPage />);
    await screen.findByText(/Presse A/);
    fireEvent.click(screen.getByRole('button', { name: /Approuver/ }));
    await waitFor(() => expect(screen.queryByText(/Presse A/)).toBeNull());
    expect(mockToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Statut approuvé' })
    );
  });

  it('shows an error toast when approve fails', async () => {
    mockFetchSequence(
      { ok: true, json: async () => ({ items: [mkItem()] }) },
      { ok: false }
    );
    render(<MachineStatusRequestsPage />);
    await screen.findByText(/Presse A/);
    fireEvent.click(screen.getByRole('button', { name: /Approuver/ }));
    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Erreur', variant: 'destructive' })
      )
    );
    expect(screen.getByText(/Presse A/)).toBeTruthy();
  });

  it('opens the reject note row, submits it, and removes the item', async () => {
    mockFetchSequence(
      { ok: true, json: async () => ({ items: [mkItem()] }) },
      { ok: true }
    );
    render(<MachineStatusRequestsPage />);
    await screen.findByText(/Presse A/);
    fireEvent.click(screen.getByRole('button', { name: /Rejeter/ }));

    const textarea = screen.getByPlaceholderText('Motif du rejet (optionnel)');
    fireEvent.change(textarea, { target: { value: 'Pas nécessaire' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }));

    await waitFor(() => expect(screen.queryByText(/Presse A/)).toBeNull());
    expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({ title: 'Demande rejetée' }));
  });

  it('toggles the reject note row closed when clicking Rejeter twice', async () => {
    mockFetchSequence({ ok: true, json: async () => ({ items: [mkItem()] }) });
    render(<MachineStatusRequestsPage />);
    await screen.findByText(/Presse A/);
    fireEvent.click(screen.getByRole('button', { name: /Rejeter/ }));
    expect(screen.getByPlaceholderText('Motif du rejet (optionnel)')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /Rejeter/ }));
    expect(screen.queryByPlaceholderText('Motif du rejet (optionnel)')).toBeNull();
  });

  it('reloads data when clicking Actualiser', async () => {
    const fetchMock = mockFetchSequence(
      { ok: true, json: async () => ({ items: [] }) },
      { ok: true, json: async () => ({ items: [mkItem()] }) }
    );
    render(<MachineStatusRequestsPage />);
    await screen.findByText('Aucune demande en attente');
    fireEvent.click(screen.getByRole('button', { name: 'Actualiser' }));
    await screen.findByText(/Presse A/);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
