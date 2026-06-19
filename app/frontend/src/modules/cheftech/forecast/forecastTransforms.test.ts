import { describe, it, expect } from 'vitest';
import { formatHours, formatCurrency, labelOverload } from './forecastTransforms';

describe('formatHours', () => {
  it('formats zero', () => expect(formatHours(0)).toBe('0 h'));
  it('rounds to 1 decimal', () => expect(formatHours(12.567)).toBe('12.6 h'));
  it('formats large number', () => expect(formatHours(100)).toBe('100 h'));
});

describe('formatCurrency', () => {
  it('formats euros', () => expect(formatCurrency(1500)).toContain('1'));
  it('returns string', () => expect(typeof formatCurrency(50)).toBe('string'));
});

describe('labelOverload', () => {
  it('overload true → warning label', () => expect(labelOverload(true)).toContain('!'));
  it('overload false → ok label', () => expect(labelOverload(false)).not.toContain('!'));
});
