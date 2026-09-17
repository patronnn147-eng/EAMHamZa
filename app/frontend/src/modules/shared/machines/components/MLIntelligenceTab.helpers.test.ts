import { describe, expect, it } from 'vitest';
import {
  anomalyBarFill,
  describeAnomalyConsensus,
  formatDaysLabel,
  formatDeltaLabel,
  formatWindowLabel,
  summariseFailureTypes,
} from './MLIntelligenceTab';

describe('formatDeltaLabel', () => {
  it('returns a dash for null/undefined', () => {
    expect(formatDeltaLabel(null)).toBe('—');
    expect(formatDeltaLabel(undefined)).toBe('—');
  });

  it('prefixes a positive delta with +', () => {
    expect(formatDeltaLabel(5.4)).toBe('+5.4 pts');
  });

  it('does not add a sign for a negative delta', () => {
    expect(formatDeltaLabel(-3.2)).toBe('-3.2 pts');
  });

  it('does not add a sign for zero', () => {
    expect(formatDeltaLabel(0)).toBe('0.0 pts');
  });
});

describe('formatDaysLabel', () => {
  it('returns null for null/undefined', () => {
    expect(formatDaysLabel(null)).toBeNull();
    expect(formatDaysLabel(undefined)).toBeNull();
  });

  it('uses singular "day" for 1', () => {
    expect(formatDaysLabel(1)).toBe('1 day ago');
  });

  it('uses plural "days" for other values', () => {
    expect(formatDaysLabel(0)).toBe('0 days ago');
    expect(formatDaysLabel(5)).toBe('5 days ago');
  });
});

describe('formatWindowLabel', () => {
  it('reports remaining days within the recovery window', () => {
    expect(formatWindowLabel(true, 2)).toBe('5 days remaining');
  });

  it('uses singular "day" when exactly one day remains', () => {
    expect(formatWindowLabel(true, 6)).toBe('1 day remaining');
  });

  it('clamps to zero when days already exceed the window', () => {
    expect(formatWindowLabel(true, 10)).toBe('0 days remaining');
  });

  it('reports "Window closed" when not within the window', () => {
    expect(formatWindowLabel(false, 2)).toBe('Window closed');
  });

  it('reports "Window closed" when days is null even if withinWindow is true', () => {
    expect(formatWindowLabel(true, null)).toBe('Window closed');
  });
});

describe('anomalyBarFill', () => {
  it('uses a bounded percentile when one is supplied', () => {
    // Machine 20: distance 23.29 at the 96.6th percentile. The old
    // max = Math.max(5, value) made this a full bar for any value over 5.
    expect(anomalyBarFill(23.29, undefined, 96.63)).toBeCloseTo(96.63);
  });

  it('clamps a percentile to 0-100', () => {
    expect(anomalyBarFill(1, undefined, 140)).toBe(100);
    expect(anomalyBarFill(1, undefined, -20)).toBe(0);
  });

  it('still scales against a genuine ceiling', () => {
    expect(anomalyBarFill(0.34, 1)).toBeCloseTo(34);
    expect(anomalyBarFill(2, 1)).toBe(100);
  });

  it('draws an empty track for an unbounded value with no scale', () => {
    expect(anomalyBarFill(23.29)).toBe(0);
    expect(anomalyBarFill(23.29, 0)).toBe(0);
    expect(anomalyBarFill(23.29, undefined, null)).toBe(0);
  });
});

describe('summariseFailureTypes', () => {
  it('names the detected failure mode in plain language', () => {
    // Machine 20's real classifier output — the case that used to render as
    // "—" / "No active failure mode".
    const result = summariseFailureTypes({
      TWF: { detected: false, probability: 0 },
      HDF: { detected: false, probability: 0 },
      PWF: { detected: true, probability: 97.2 },
      OSF: { detected: false, probability: 0 },
      RNF: { detected: false, probability: 0 },
    });
    expect(result.label).toBe('Power failure');
    expect(result.detail).toBe('97% confidence');
  });

  it('lists every detected mode, most likely first', () => {
    const result = summariseFailureTypes({
      TWF: { detected: true, probability: 60 },
      HDF: { detected: true, probability: 80 },
    });
    expect(result.label).toBe('Overheating / Tool wear');
    expect(result.detail).toBe('80% confidence');
  });

  it('names the closest mode when nothing is detected', () => {
    const result = summariseFailureTypes({
      TWF: { detected: false, probability: 12 },
      HDF: { detected: false, probability: 3 },
    });
    expect(result.label).toBe('None detected');
    expect(result.detail).toBe('Closest: Tool wear at 12%');
  });

  it('says so when the classifier returned nothing', () => {
    expect(summariseFailureTypes(null).label).toBe('—');
    expect(summariseFailureTypes({}).detail).toBe('Classification unavailable');
  });
});

describe('describeAnomalyConsensus', () => {
  it('reports deviation when the ensemble flags the machine', () => {
    expect(describeAnomalyConsensus({}, true)).toBe(
      'Machine behaviour deviates from normal operating pattern.',
    );
  });

  it('surfaces dissenting detectors instead of claiming agreement', () => {
    // Machine 20: low ensemble score, but every trend detector alarming and a
    // Mahalanobis reading in the top few percent.
    const text = describeAnomalyConsensus(
      {
        conflict_factor_K: 0.4298,
        model_outputs: {
          anomaly: {
            cusum_alarms: {
              air_temperature: true,
              process_temperature: true,
              rotational_speed: true,
              torque: true,
              tool_wear: true,
            },
          },
          mahal_hi: { percentile_rank: 0.9663 },
        },
      },
      false,
    );
    expect(text).toContain('5 of 5 sensor trends are drifting');
    expect(text).toContain('more unusual than 97% of past readings');
    expect(text).not.toContain('agree');
  });

  it('falls back to model conflict when no single detector dissents', () => {
    const text = describeAnomalyConsensus({ conflict_factor_K: 0.5 }, false);
    expect(text).toContain('the models disagree about this reading');
  });

  it('claims agreement only when nothing dissents', () => {
    const text = describeAnomalyConsensus(
      {
        conflict_factor_K: 0.05,
        model_outputs: {
          anomaly: { cusum_alarms: { torque: false, tool_wear: false } },
          mahal_hi: { percentile_rank: 0.4 },
        },
      },
      false,
    );
    expect(text).toBe('Every detector agrees: machine within normal operating range.');
  });
});
