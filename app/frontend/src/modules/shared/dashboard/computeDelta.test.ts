import { describe, expect, it } from 'vitest';
import { computeDelta } from './computeDelta';

describe('computeDelta', () => {
  it('reports an increase', () => {
    expect(computeDelta(5, 3)).toEqual({ direction: 'up', amount: 2, label: '▲ 2' });
  });
  it('reports a decrease', () => {
    expect(computeDelta(3, 5)).toEqual({ direction: 'down', amount: 2, label: '▼ 2' });
  });
  it('reports no change', () => {
    expect(computeDelta(4, 4)).toEqual({ direction: 'flat', amount: 0, label: '–' });
  });
  it('treats a missing previous as flat', () => {
    expect(computeDelta(4)).toEqual({ direction: 'flat', amount: 0, label: '–' });
  });
});
