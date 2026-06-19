export interface DashboardFilterState {
  range: '7d' | '30d' | '90d';
  site: string;
}

export const DEFAULT_FILTERS: DashboardFilterState = { range: '7d', site: 'all' };

const keyFor = (userId: string) => `eam.dashboard.filters.${userId}`;

export function loadFilters(userId: string): DashboardFilterState {
  try {
    const raw = localStorage.getItem(keyFor(userId));
    if (!raw) return DEFAULT_FILTERS;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.range !== 'string' || typeof parsed.site !== 'string') {
      return DEFAULT_FILTERS;
    }
    return { range: parsed.range, site: parsed.site };
  } catch {
    return DEFAULT_FILTERS;
  }
}

export function saveFilters(userId: string, state: DashboardFilterState): void {
  try {
    localStorage.setItem(keyFor(userId), JSON.stringify(state));
  } catch {
    /* storage full / unavailable — non-fatal */
  }
}
