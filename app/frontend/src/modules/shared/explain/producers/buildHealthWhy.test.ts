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
    expect(p.counterfactual?.length).toBeGreaterThan(0);
  });
  it('counterfactual targets the out-of-range sensor', () => {
    const p = buildHealthWhy(health);
    const cf = p.counterfactual.map((r) => r.label).join(' ');
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

  // Regression: machine 20 in eam-staging returned verdict Critical with every
  // sensor NORMAL. The panel showed "Risque de panne élevé" above "Aucun signal
  // préoccupant", and "Expliquer simplement" had nothing to send.
  describe('verdict at risk while every sensor reads normal', () => {
    const criticalButNormalSensors: UnifiedHealthLike = {
      dst_verdict: 'Critical',
      conflict_factor_K: 0.4298,
      is_anomaly: false,
      sensor_status: [
        { key: 'air_temperature', label: 'Température air', value: 29.9, unit: '°C', status: 'NORMAL', target: 31.85 },
        { key: 'process_temperature', label: 'Température procédé', value: 39.1, unit: '°C', status: 'NORMAL', target: 41.85 },
        { key: 'rotational_speed', label: 'Vitesse rotation', value: 1478, unit: 'tr/min', status: 'NORMAL', target: 1700 },
        { key: 'torque', label: 'Couple', value: 55.4, unit: 'Nm', status: 'NORMAL', target: 60 },
        { key: 'tool_wear', label: 'Usure outil', value: 161, unit: 'min', status: 'NORMAL', target: 200 },
      ],
      explanations: [
        { factor: "Usure de l'Outil", impact: -2.68, intensity: 'high' },
        { factor: 'temp_delta', impact: -1.83, intensity: 'high' },
        { factor: 'Vitesse de Rotation', impact: -1.36, intensity: 'high' },
      ],
    };

    it('gives reasons instead of an empty list', () => {
      const p = buildHealthWhy(criticalButNormalSensors);
      expect(p.reasons.length).toBeGreaterThan(0);
    });

    it('does not claim nothing is wrong under an at-risk title', () => {
      const p = buildHealthWhy(criticalButNormalSensors);
      expect(p.summary).not.toContain('Aucun signal préoccupant');
    });

    it('gives the explain button something to send', () => {
      const p = buildHealthWhy(criticalButNormalSensors);
      expect((p.llmContext?.reasons as string[]).length).toBeGreaterThan(0);
    });

    it('renders raw model factor keys as readable French', () => {
      const p = buildHealthWhy(criticalButNormalSensors);
      const text = JSON.stringify(p);
      expect(text).not.toContain('temp_delta');
      expect(text).toContain('Écart entre température');
    });

    it('still leaks no ML jargon on this path', () => {
      const p = buildHealthWhy(criticalButNormalSensors);
      expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
    });
  });

  it('stays quiet when the machine really is healthy', () => {
    const p = buildHealthWhy({
      dst_verdict: 'Healthy',
      sensor_status: [
        { key: 'torque', label: 'Couple', value: 10, unit: 'Nm', status: 'NORMAL', target: 60 },
      ],
      explanations: [],
    });
    expect(p.reasons).toEqual([]);
    expect(p.summary).toContain('Aucun signal préoccupant');
  });
});
