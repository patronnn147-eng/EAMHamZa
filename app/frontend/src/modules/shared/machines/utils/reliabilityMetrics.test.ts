import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Intervention } from '@/lib/types';
import {
  computeFleetKpiTrends,
  computeFleetReliability,
  computeReliabilityMetrics,
  formatDuration,
  formatHours,
} from './reliabilityMetrics';

const NOW = new Date('2026-07-24T12:00:00.000Z').getTime();

function mkIntervention(
  id: number,
  startOffsetHours: number,
  durationMinutes: number,
  overrides: Partial<Intervention> = {}
): Intervention {
  const start = new Date(NOW - startOffsetHours * 3600_000);
  const end = new Date(start.getTime() + durationMinutes * 60_000);
  return {
    id,
    date_intervention: start.toISOString(),
    date_debut: start.toISOString(),
    date_fin: end.toISOString(),
    rapport: 'r',
    created_at: start.toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('formatDuration', () => {
  it('shows <1m for sub-minute durations', () => {
    expect(formatDuration(0.5)).toBe('<1m');
  });
  it('shows minutes only under an hour', () => {
    expect(formatDuration(45)).toBe('45m');
  });
  it('shows hours only on exact hours', () => {
    expect(formatDuration(120)).toBe('2h');
  });
  it('shows hours and minutes', () => {
    expect(formatDuration(150)).toBe('2h 30m');
  });
});

describe('formatHours', () => {
  it('shows minutes under an hour', () => {
    expect(formatHours(0.5)).toBe('30m');
  });
  it('shows hours only under a day', () => {
    expect(formatHours(5)).toBe('5h');
  });
  it('shows days only on exact days', () => {
    expect(formatHours(48)).toBe('2j');
  });
  it('shows days and hours', () => {
    expect(formatHours(50)).toBe('2j 2h');
  });
});

describe('computeReliabilityMetrics', () => {
  it('returns a perfect score with no interventions', () => {
    const m = computeReliabilityMetrics([], 90);
    expect(m.failureCount).toBe(0);
    expect(m.mttr).toBeNull();
    expect(m.mtbf).toBeNull();
    expect(m.uptimePct).toBe(100);
    expect(m.reliabilityScore).toBe(100);
    expect(m.classification).toBe('Excellent');
  });

  it('ignores interventions outside the window and without both timestamps', () => {
    const outsideWindow = mkIntervention(1, 200 * 24, 60);
    const noEnd = mkIntervention(2, 10, 60, { date_fin: undefined });
    const m = computeReliabilityMetrics([outsideWindow, noEnd], 90);
    expect(m.failureCount).toBe(0);
  });

  it('computes MTTR and MTBF from two failures', () => {
    const first = mkIntervention(1, 48, 60); // 48h ago, 1h downtime
    const second = mkIntervention(2, 24, 30); // 24h ago, 30m downtime
    const m = computeReliabilityMetrics([first, second], 90);
    expect(m.failureCount).toBe(2);
    expect(m.mttr).toBe(45); // (60+30)/2
    expect(m.mtbf).not.toBeNull();
    expect(m.totalDowntimeMinutes).toBe(90);
  });

  it('computes MTBF as window-minus-downtime for a single failure', () => {
    const only = mkIntervention(1, 10, 60);
    const m = computeReliabilityMetrics([only], 90);
    expect(m.failureCount).toBe(1);
    expect(m.mtbf).toBeCloseTo(90 * 24 - 1, 5);
  });

  it('classifies as Critique with heavy downtime', () => {
    const events = Array.from({ length: 20 }, (_, i) => mkIntervention(i, i * 2, 2000));
    const m = computeReliabilityMetrics(events, 90);
    expect(m.classification).toBe('Critique');
    expect(m.colorClass).toContain('red');
  });

  it('sorts downtime events newest-first', () => {
    const older = mkIntervention(1, 48, 30);
    const newer = mkIntervention(2, 5, 30);
    const m = computeReliabilityMetrics([older, newer], 90);
    expect(m.downtimeEvents[0].id).toBe(2);
    expect(m.downtimeEvents[1].id).toBe(1);
  });

  it('drops zero-duration events', () => {
    const zero = mkIntervention(1, 5, 0);
    const m = computeReliabilityMetrics([zero], 90);
    expect(m.failureCount).toBe(0);
  });
});

describe('computeFleetReliability', () => {
  it('defaults to 100% uptime with no machines', () => {
    const summary = computeFleetReliability([], {});
    expect(summary.avgUptimePct).toBe(100);
    expect(summary.avgMttr).toBeNull();
    expect(summary.avgMtbf).toBeNull();
    expect(summary.entries).toHaveLength(0);
  });

  it('aggregates per-machine metrics and counts classifications', () => {
    const machines = [{ id: 1, nom: 'M1' }, { id: 2, nom: 'M2' }];
    const interventionsByMachineId = {
      1: [mkIntervention(1, 10, 30)],
      2: [] as Intervention[],
    };
    const summary = computeFleetReliability(machines, interventionsByMachineId, 90);
    expect(summary.entries).toHaveLength(2);
    expect(summary.goodCount + summary.criticalCount).toBeLessThanOrEqual(2);
    expect(summary.totalDowntimeMinutes).toBe(30);
    expect(summary.avgMttr).toBe(30);
  });
});

describe('computeFleetKpiTrends', () => {
  it('produces empty-safe series with no machines', () => {
    const trends = computeFleetKpiTrends([], {});
    expect(trends.availability.series).toHaveLength(13);
    expect(trends.mttr.current).toBe(0);
    expect(trends.mtbf.current).toBe(0);
    expect(trends.downtime.current).toBe(0);
  });

  it('buckets recent downtime into the weekly series and current/previous periods', () => {
    const machines = [{ id: 1, nom: 'M1' }];
    const interventionsByMachineId = {
      1: [mkIntervention(1, 2, 120), mkIntervention(2, 100 * 24, 60)],
    };
    const trends = computeFleetKpiTrends(machines, interventionsByMachineId, 180, 13);
    expect(trends.downtime.current).toBe(120);
    expect(trends.downtime.previous).toBe(60);
    expect(trends.downtime.pctChange).toBeCloseTo(100, 0);
    expect(trends.mttr.goodDirection).toBe('down');
    expect(trends.mtbf.goodDirection).toBe('up');
    expect(trends.availability.target).toBe(95);
  });

  it('reports null pctChange when previous period has no data', () => {
    const machines = [{ id: 1, nom: 'M1' }];
    const interventionsByMachineId = { 1: [mkIntervention(1, 2, 120)] };
    const trends = computeFleetKpiTrends(machines, interventionsByMachineId, 180, 13);
    expect(trends.downtime.previous).toBe(0);
    expect(trends.mttr.pctChange).toBeNull();
  });
});
