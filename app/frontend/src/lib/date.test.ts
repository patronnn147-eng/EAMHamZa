import { describe, expect, it } from 'vitest';
import { toDateInputValue, toDateTimeLocalInputValue } from './date';

describe('toDateInputValue', () => {
  it('returns empty string for null/undefined', () => {
    expect(toDateInputValue(null)).toBe('');
    expect(toDateInputValue()).toBe('');
    expect(toDateInputValue('')).toBe('');
  });

  it('passes through an already YYYY-MM-DD value', () => {
    expect(toDateInputValue('2026-01-29')).toBe('2026-01-29');
  });

  it('truncates an ISO datetime string', () => {
    expect(toDateInputValue('2026-01-29T00:00:00Z')).toBe('2026-01-29');
  });

  it('parses and normalizes an arbitrary date string', () => {
    expect(toDateInputValue('January 29, 2026 12:00:00 UTC')).toBe('2026-01-29');
  });

  it('returns empty string for an invalid date', () => {
    expect(toDateInputValue('not-a-date')).toBe('');
  });
});

describe('toDateTimeLocalInputValue', () => {
  it('returns empty string for null/undefined', () => {
    expect(toDateTimeLocalInputValue(null)).toBe('');
    expect(toDateTimeLocalInputValue()).toBe('');
    expect(toDateTimeLocalInputValue('')).toBe('');
  });

  it('returns empty string for an invalid date', () => {
    expect(toDateTimeLocalInputValue('garbage')).toBe('');
  });

  it('formats a valid ISO datetime into local YYYY-MM-DDTHH:mm', () => {
    const input = '2026-03-05T14:30:00Z';
    const d = new Date(input);
    const expected = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    expect(toDateTimeLocalInputValue(input)).toBe(expected);
  });
});
