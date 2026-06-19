import { describe, expect, it } from 'vitest';
import { buildNbaWhy } from './buildNbaWhy';
import { NO_JARGON } from '../plainLanguage';

describe('buildNbaWhy', () => {
  it('explains a critical action in plain words', () => {
    const p = buildNbaWhy({ key: 'alert-7', label: 'Alerte critique — machine 7', severity: 'critical', href: '/machines/7', score: 100 });
    expect(p.title).toBeTruthy();
    expect(p.reasons.length).toBeGreaterThan(0);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
});
