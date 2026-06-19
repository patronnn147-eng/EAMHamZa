import { describe, expect, it } from 'vitest';
import { buildHealthWhy, UnifiedHealthLike } from './buildHealthWhy';
import { NO_JARGON } from '../plainLanguage';

const health: UnifiedHealthLike = {
  dst_verdict: 'Critical',
  conflict_factor_K: 0.1,
  is_anomaly: true,
  sensor_status: [
    { key: 'process_temperature', label: 'Température procédé', value: 45, unit: '°C', status: 'CRITIQUE', target: 35 },
    { key: 'torque', label: 'Couple', value: 10, unit: 'Nm', status: 'NORMAL', target: 18 },
  ],
  explanations: [{ factor: 'process_temperature', impact: 0.31, intensity: 'high' }],
};

describe('buildHealthWhy', () => {
  it('produces a plain payload with confidence and counterfactual', () => {
    const p = buildHealthWhy(health);
    expect(p.title).toBeTruthy();
    expect(p.confidence?.level).toBe('Élevée');
    expect(p.counterfactual && p.counterfactual.length).toBeGreaterThan(0);
  });
  it('counterfactual targets the out-of-range sensor', () => {
    const p = buildHealthWhy(health);
    const cf = p.counterfactual!.map((r) => r.label).join(' ');
    expect(cf.toLowerCase()).toContain('procédé');
  });
  it('never leaks ML jargon', () => {
    const p = buildHealthWhy(health);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
  it('degrades to a minimal payload with no data', () => {
    const p = buildHealthWhy({});
    expect(p.title).toBeTruthy();
    expect(p.reasons).toEqual([]);
  });
});
