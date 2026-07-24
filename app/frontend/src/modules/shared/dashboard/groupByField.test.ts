import { describe, expect, it } from 'vitest';
import { groupByField, relabelSlices } from './groupByField';

describe('groupByField', () => {
  it('counts occurrences per key, sorted descending', () => {
    const items = [{ s: 'A' }, { s: 'B' }, { s: 'A' }, { s: 'A' }];
    const result = groupByField(items, (i) => i.s);
    expect(result).toEqual([
      { name: 'A', value: 3 },
      { name: 'B', value: 1 },
    ]);
  });

  it('buckets null/undefined keys under the "Other" label', () => {
    const items = [{ s: null }, { s: undefined }, { s: 'A' }];
    const result = groupByField(items, (i) => i.s);
    expect(result).toEqual([
      { name: 'Other', value: 2 },
      { name: 'A', value: 1 },
    ]);
  });

  it('uses a custom otherLabel', () => {
    const items = [{ s: null }];
    const result = groupByField(items, (i) => i.s, {}, 'Inconnu');
    expect(result).toEqual([{ name: 'Inconnu', value: 1 }]);
  });

  it('relabels raw keys via labelMap', () => {
    const items = [{ s: 'EN_ATTENTE' }, { s: 'PENDING' }];
    const result = groupByField(items, (i) => i.s, { EN_ATTENTE: 'Pending', PENDING: 'Pending' });
    expect(result).toEqual([{ name: 'Pending', value: 2 }]);
  });

  it('returns an empty array for empty input', () => {
    expect(groupByField([], () => 'x')).toEqual([]);
  });
});

describe('relabelSlices', () => {
  it('passes through slices unchanged when no maps are given', () => {
    const slices = [{ name: 'A', value: 3 }, { name: 'B', value: 1 }];
    expect(relabelSlices(slices)).toEqual([
      { name: 'A', value: 3, color: undefined },
      { name: 'B', value: 1, color: undefined },
    ]);
  });

  it('merges slices that map to the same label', () => {
    const slices = [
      { name: 'EN_ATTENTE', value: 2 },
      { name: 'PENDING', value: 3 },
    ];
    const result = relabelSlices(slices, { EN_ATTENTE: 'Pending', PENDING: 'Pending' });
    expect(result).toEqual([{ name: 'Pending', value: 5, color: undefined }]);
  });

  it('attaches colors from colorMap by final label', () => {
    const slices = [{ name: 'A', value: 1 }];
    const result = relabelSlices(slices, {}, { A: '#fff' });
    expect(result).toEqual([{ name: 'A', value: 1, color: '#fff' }]);
  });

  it('sorts merged results descending by value', () => {
    const slices = [
      { name: 'Low', value: 1 },
      { name: 'High', value: 9 },
    ];
    const result = relabelSlices(slices);
    expect(result.map((s) => s.name)).toEqual(['High', 'Low']);
  });
});
