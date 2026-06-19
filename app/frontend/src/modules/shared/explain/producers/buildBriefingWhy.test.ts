import { describe, expect, it } from 'vitest';
import { buildBriefingWhy } from './buildBriefingWhy';
import { NO_JARGON } from '../plainLanguage';

describe('buildBriefingWhy', () => {
  it('turns facts into plain reasons', () => {
    const p = buildBriefingWhy({ urgent_wos: 2, overdue_pms: 1, degraded_machines: ['P-07'], active_alerts: 0 });
    const labels = p.reasons.map((r) => r.label).join(' ');
    expect(labels).toMatch(/urgent/i);
    expect(NO_JARGON.test(JSON.stringify(p))).toBe(false);
  });
  it('reassures with no facts', () => {
    const p = buildBriefingWhy({ urgent_wos: 0, overdue_pms: 0, degraded_machines: [], active_alerts: 0 });
    expect(p.reasons).toEqual([]);
  });
});
