import { describe, expect, it } from 'vitest';
import {
  formatDaysLabel,
  formatDeltaLabel,
  formatWindowLabel,
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
