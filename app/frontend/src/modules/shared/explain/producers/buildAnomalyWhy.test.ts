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
});
