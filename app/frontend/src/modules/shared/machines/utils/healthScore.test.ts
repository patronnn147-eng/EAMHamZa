import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Machine } from '@/lib/types';
import { computeHealthScore, computeHealthScoreFromML, formatDuration } from './healthScore';

const NOW = new Date('2026-07-24T12:00:00.000Z').getTime();

function mkMachine(overrides: Partial<Machine> = {}): Machine {
  return {
    id: 1,
    nom: 'M1',
    statut: 'OPERATIONNEL',
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
  it('handles negative days as Aucune', () => {
    expect(formatDuration(-1)).toBe('Aucune');
  });
  it('handles zero as Aujourd\'hui', () => {
    expect(formatDuration(0)).toBe("Aujourd'hui");
  });
  it('handles one as Hier', () => {
    expect(formatDuration(1)).toBe('Hier');
  });
  it('handles under a month in days', () => {
    expect(formatDuration(15)).toBe('15 jours');
  });
  it('handles under a year in months', () => {
    expect(formatDuration(60)).toBe('2 mois');
  });
  it('handles a year as singular "an"', () => {
    expect(formatDuration(365)).toBe('1 an');
  });
  it('handles multiple years as plural "ans"', () => {
    expect(formatDuration(800)).toBe('2 ans');
  });
});

describe('computeHealthScore (basic operational, no ML data)', () => {
  it('scores a fresh machine near 100 with no deductions', () => {
    const m = mkMachine();
    const result = computeHealthScore(m, 0, 0);
    expect(result.score).toBe(100);
    expect(result.label).toBe('Bonne Condition');
    expect(result.factors.isDown).toBe(false);
  });

  it('deducts for days since last maintenance, capped at 30', () => {
    const longAgo = new Date(NOW - 200 * 24 * 60 * 60 * 1000).toISOString();
    const m = mkMachine({ date_derniere_maintenance: longAgo });
    const result = computeHealthScore(m, 0, 0);
    expect(result.deductions.maintenance).toBe(30);
  });

  it('deducts for open work orders, capped at 36', () => {
    const m = mkMachine();
    const result = computeHealthScore(m, 10, 0);
    expect(result.deductions.workOrders).toBe(36);
  });

  it('deducts for recent interventions, capped at 30', () => {
    const m = mkMachine();
    const result = computeHealthScore(m, 0, 10);
    expect(result.deductions.interventions).toBe(30);
  });

  it('applies a status deduction when the machine is down', () => {
    const m = mkMachine({ statut: 'EN_PANNE' });
    const result = computeHealthScore(m, 0, 0);
    expect(result.deductions.status).toBe(60);
    expect(result.factors.isDown).toBe(true);
    expect(result.label).toBe('État Critique');
  });

  it('treats HORS_SERVICE as down too', () => {
    const m = mkMachine({ statut: 'HORS_SERVICE' });
    const result = computeHealthScore(m, 0, 0);
    expect(result.factors.isDown).toBe(true);
  });

  it('adds an overdue deduction when next maintenance date has passed, capped at 40', () => {
    const overdueDate = new Date(NOW - 100 * 24 * 60 * 60 * 1000).toISOString();
    const m = mkMachine({ date_prochaine_maintenance: overdueDate });
    const result = computeHealthScore(m, 0, 0);
    expect(result.deductions.overdue).toBe(40);
  });

  it('does not add an overdue deduction when next maintenance is in the future', () => {
    const future = new Date(NOW + 10 * 24 * 60 * 60 * 1000).toISOString();
    const m = mkMachine({ date_prochaine_maintenance: future });
    const result = computeHealthScore(m, 0, 0);
    expect(result.deductions.overdue).toBe(0);
  });

  it('clamps score at 0 with maximum stacked deductions', () => {
    const longAgo = new Date(NOW - 200 * 24 * 60 * 60 * 1000).toISOString();
    const overdueDate = new Date(NOW - 100 * 24 * 60 * 60 * 1000).toISOString();
    const m = mkMachine({
      statut: 'EN_PANNE',
      date_derniere_maintenance: longAgo,
      date_prochaine_maintenance: overdueDate,
    });
    const result = computeHealthScore(m, 10, 10);
    expect(result.score).toBe(0);
    expect(result.label).toBe('État Critique');
  });

  it('lands in Attention Requise for a mid-range score', () => {
    const m = mkMachine();
    const result = computeHealthScore(m, 2, 0); // 24 pts deduction -> score 76
    expect(result.score).toBe(76);
    expect(result.label).toBe('Attention Requise');
  });

  it('delegates to the ML mapper when ML data is supplied', () => {
    const m = mkMachine();
    const result = computeHealthScore(m, 0, 0, { health_score: 65 });
    expect(result.label).toBe('Attention Requise (IA)');
  });
});

describe('computeHealthScoreFromML', () => {
  it('returns neutral health when no ML data is provided', () => {
    const m = mkMachine();
    const result = computeHealthScoreFromML(m, null);
    expect(result.score).toBe(100);
    expect(result.label).toBe('Analyse en cours...');
  });

  it('prefers unified_health_score over legacy health_score', () => {
    const m = mkMachine();
    const result = computeHealthScoreFromML(m, { unified_health_score: 40, health_score: 90 });
    expect(result.score).toBe(40);
    expect(result.score_source).toBe('dst_fusion');
  });

  it('falls back to legacy health_score and fallback_additive source when unified score is absent', () => {
    const m = mkMachine();
    const result = computeHealthScoreFromML(m, { health_score: 85 });
    expect(result.score).toBe(85);
    expect(result.score_source).toBe('fallback_additive');
    expect(result.label).toBe('Bonne Condition (IA)');
  });

  it('clamps score into 0-100 range', () => {
    const m = mkMachine();
    const result = computeHealthScoreFromML(m, { unified_health_score: 150 });
    expect(result.score).toBe(100);
  });

  it('pulls factors and deductions from health_breakdown when present', () => {
    const m = mkMachine();
    const result = computeHealthScoreFromML(m, {
      unified_health_score: 70,
      health_breakdown: {
        days_since_maintenance: 12,
        open_work_orders: 2,
        recent_interventions: 1,
        maintenance_deduction: 5,
        dst_verdict: 'Degrading',
        conflict_factor_K: 0.3,
      },
    });
    expect(result.factors.daysSinceLastMaintenance).toBe(12);
    expect(result.factors.openWorkOrders).toBe(2);
    expect(result.deductions.maintenance).toBe(5);
    expect(result.dst_verdict).toBe('Degrading');
    expect(result.conflict_k).toBe(0.3);
  });

  it('marks isDown based on machine status regardless of ML data', () => {
    const m = mkMachine({ statut: 'EN_PANNE' });
    const result = computeHealthScoreFromML(m, { unified_health_score: 90 });
    expect(result.factors.isDown).toBe(true);
  });
});
