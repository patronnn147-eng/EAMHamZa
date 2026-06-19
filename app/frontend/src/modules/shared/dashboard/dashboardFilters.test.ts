import { describe, expect, it, beforeEach } from 'vitest';

// Minimal in-memory localStorage — the test runner uses the node environment,
// which has no DOM. Keeps this a dependency-free pure-logic test.
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
  clear: () => { store.clear(); },
};

import { loadFilters, saveFilters, DEFAULT_FILTERS, DashboardFilterState } from './dashboardFilters';

beforeEach(() => localStorage.clear());

describe('dashboardFilters', () => {
  it('returns defaults when nothing is stored', () => {
    expect(loadFilters('u1')).toEqual(DEFAULT_FILTERS);
  });

  it('round-trips a saved value per user', () => {
    const f: DashboardFilterState = { range: '30d', site: 'tunis-1' };
    saveFilters('u1', f);
    expect(loadFilters('u1')).toEqual(f);
    expect(loadFilters('u2')).toEqual(DEFAULT_FILTERS); // scoped per user
  });

  it('falls back to defaults on corrupt storage', () => {
    localStorage.setItem('eam.dashboard.filters.u1', '{not json');
    expect(loadFilters('u1')).toEqual(DEFAULT_FILTERS);
  });
});
