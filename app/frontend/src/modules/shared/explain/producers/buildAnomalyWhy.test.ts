import { describe, expect, it } from 'vitest';
import { buildAnomalyWhy } from './buildAnomalyWhy';
import { NO_JARGON } from '../plainLanguage';

describe('buildAnomalyWhy', () => {
  it('lists abnormal sensors in plain words, no jargon', () => {
    const p = buildAnomalyWhy({
      is_anomaly: true,
      sensor_status: [
        { key: 'process_temperature', label: 'Température procédé', value: 45, unit: '°C', status: 'CRITIQUE', target: 35 },
        { key: 'torque', label: 'Couple', value: 10, unit: 'Nm', status: 'NORMAL', target: 18 },
      ],
    });
    expect(p.reasons.length).toBe(1);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
  it('reassures when nothing is abnormal', () => {
    const p = buildAnomalyWhy({ is_anomaly: false, sensor_status: [] });
    expect(p.summary).toBeTruthy();
    expect(p.reasons).toEqual([]);
  });

  // Regression: a machine with every sensor NORMAL produced an empty drawer, so
  // "Expliquer simplement" posted an empty list and the endpoint answered
  // "Aucune raison particuliere a signaler." — which reads as a failure.
  describe('all sensors normal but sensors are present', () => {
    const normal = {
      is_anomaly: false,
      sensor_status: [
        { key: 'air_temperature', label: 'Température air', value: 29.9, unit: '°C', status: 'NORMAL' as const, target: 31.85 },
        { key: 'torque', label: 'Couple', value: 55.4, unit: 'Nm', status: 'NORMAL' as const, target: 60 },
      ],
    };

    it('states what was checked instead of showing nothing', () => {
      const p = buildAnomalyWhy(normal);
      expect(p.reasons.length).toBeGreaterThan(0);
      expect(p.reasons[0].label).toContain('2 mesures vérifiées');
    });

    it('still reads as normal, not as a problem', () => {
      const p = buildAnomalyWhy(normal);
      expect(p.title).toBe('Comportement normal');
      expect(p.summary).toContain('comme d’habitude');
    });

    it('gives the explain button something to send', () => {
      const p = buildAnomalyWhy(normal);
      expect((p.llmContext?.reasons as string[]).length).toBeGreaterThan(0);
    });

    it('leaks no ML jargon', () => {
      expect(NO_JARGON.test(JSON.stringify(buildAnomalyWhy(normal)))).toBe(false);
    });
  });
});
