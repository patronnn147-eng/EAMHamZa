import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { mockToastSuccess, mockToastError } = vi.hoisted(() => ({
  mockToastSuccess: vi.fn(),
  mockToastError: vi.fn(),
}));
vi.mock('sonner', () => ({
  toast: { success: mockToastSuccess, error: mockToastError },
}));

import { AnomalyReviewQueue } from './AnomalyReviewQueue';

function mkFlag(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    machine_id: 10,
    machine_name: 'Presse A',
    anomaly_score: 0.87,
    sensor_snapshot: {
      air_temperature: 300,
      process_temperature: 310,
      rotational_speed: 1500,
      torque: 40,
      tool_wear: 10,
    },
    flagged_at: new Date().toISOString(),
    ...overrides,
  };
}

function mockFetchSequence(...responses: Array<{ ok: boolean; json?: () => Promise<unknown> }>) {
  const fn = vi.fn();
  for (const r of responses) fn.mockResolvedValueOnce(r as unknown as Response);
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}

beforeEach(() => {
  mockToastSuccess.mockReset();
  mockToastError.mockReset();
  localStorage.setItem('access_token', 'test-token');
});

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('AnomalyReviewQueue', () => {
  it('shows the empty state when the queue has no items', async () => {
    mockFetchSequence({ ok: true, json: async () => ({ pending_count: 0, items: [] }) });
    render(<AnomalyReviewQueue />);
    expect(await screen.findByText(/Aucune anomalie en attente/)).toBeTruthy();
  });

  it('renders pending flags with score and pending count', async () => {
    mockFetchSequence({
      ok: true,
      json: async () => ({ pending_count: 1, items: [mkFlag()] }),
    });
    render(<AnomalyReviewQueue />);
    expect(await screen.findByText('Presse A')).toBeTruthy();
    expect(screen.getByText('0.87')).toBeTruthy();
    expect(screen.getByText(/1 anomalie\(s\) détectée/)).toBeTruthy();
  });

  it('falls back to #machine_id when machine_name is null', async () => {
    mockFetchSequence({
      ok: true,
      json: async () => ({ pending_count: 1, items: [mkFlag({ machine_name: null, machine_id: 42 })] }),
    });
    render(<AnomalyReviewQueue />);
    expect(await screen.findByText('#42')).toBeTruthy();
  });

  it('shows a dash for a null anomaly score and null flagged_at', async () => {
    mockFetchSequence({
      ok: true,
      json: async () => ({
        pending_count: 1,
        items: [mkFlag({ anomaly_score: null, flagged_at: null })],
      }),
    });
    render(<AnomalyReviewQueue />);
    await screen.findByText('Presse A');
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBe(2);
  });

  it('stays in the loading skeleton when the fetch fails', async () => {
    mockFetchSequence({ ok: false });
    render(<AnomalyReviewQueue />);
    await waitFor(() => {});
    expect(screen.queryByText(/Aucune anomalie/)).toBeNull();
    expect(screen.queryByText('Presse A')).toBeNull();
  });

  it('stays in the loading skeleton when fetch throws', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('down')) as unknown as typeof fetch;
    render(<AnomalyReviewQueue />);
    await waitFor(() => {});
    expect(screen.queryByText(/Aucune anomalie/)).toBeNull();
  });

  it('confirms a real anomaly and removes it from the queue', async () => {
    mockFetchSequence(
      { ok: true, json: async () => ({ pending_count: 1, items: [mkFlag()] }) },
      { ok: true }
    );
    render(<AnomalyReviewQueue />);
    await screen.findByText('Presse A');
    fireEvent.click(screen.getByTitle('Anomalie réelle confirmée'));
    await waitFor(() => expect(screen.queryByText('Presse A')).toBeNull());
    expect(mockToastSuccess).toHaveBeenCalledWith('Anomalie évaluée, merci.');
  });

  it('marks a false positive via the reject button', async () => {
    mockFetchSequence(
      { ok: true, json: async () => ({ pending_count: 1, items: [mkFlag()] }) },
      { ok: true }
    );
    render(<AnomalyReviewQueue />);
    await screen.findByText('Presse A');
    fireEvent.click(screen.getByTitle('Fausse alerte'));
    await waitFor(() => expect(screen.queryByText('Presse A')).toBeNull());
    expect(mockToastSuccess).toHaveBeenCalled();
  });

  it('shows an error toast and keeps the row when the submit request fails', async () => {
    mockFetchSequence(
      { ok: true, json: async () => ({ pending_count: 1, items: [mkFlag()] }) },
      { ok: false }
    );
    render(<AnomalyReviewQueue />);
    await screen.findByText('Presse A');
    fireEvent.click(screen.getByTitle('Variation normale (démarrage, etc.)'));
    await waitFor(() => expect(mockToastError).toHaveBeenCalledWith("Échec de l'évaluation."));
    expect(screen.getByText('Presse A')).toBeTruthy();
  });

  it('decrements pending_count after a successful confirmation with items remaining', async () => {
    mockFetchSequence(
      {
        ok: true,
        json: async () => ({
          pending_count: 2,
          items: [mkFlag({ id: 1, machine_name: 'M1' }), mkFlag({ id: 2, machine_name: 'M2' })],
        }),
      },
      { ok: true }
    );
    render(<AnomalyReviewQueue />);
    await screen.findByText('M1');
    fireEvent.click(screen.getAllByTitle('Anomalie réelle confirmée')[0]);
    await waitFor(() => expect(screen.queryByText('M1')).toBeNull());
    expect(screen.getByText('M2')).toBeTruthy();
    expect(screen.getByText(/1 anomalie\(s\) détectée/)).toBeTruthy();
  });
});
