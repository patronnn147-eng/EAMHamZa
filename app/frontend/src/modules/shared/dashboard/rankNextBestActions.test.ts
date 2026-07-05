import { describe, expect, it } from 'vitest';
import { rankNextBestActions, NbaInput } from './rankNextBestActions';

const base: NbaInput = {
  role: 'CHEFTECH',
  userId: 1,
  workOrders: [
    { id: 10, priorite: 'URGENTE', statut: 'EN_ATTENTE', technicien_id: 2 },
    { id: 11, priorite: 'MOYENNE', statut: 'EN_ATTENTE', technicien_id: 1 },
  ],
  overduePMs: [{ machine_id: 5, nom: 'Press P-1' }],
  alerts: [{ type: 'ANOMALY', severity: 'CRITICAL', machine_id: 7 }],
};

describe('rankNextBestActions', () => {
  it('puts a critical alert above an urgent WO above an overdue PM', () => {
    const out = rankNextBestActions(base);
    expect(out.map((a) => a.severity)).toEqual(['critical', 'high', 'medium']);
  });

  it('caps output at 5', () => {
    const many: NbaInput = {
      ...base,
      workOrders: Array.from({ length: 9 }, (_, i) => ({
        id: i, priorite: 'URGENTE', statut: 'EN_ATTENTE', technicien_id: 1,
      })),
    };
    expect(rankNextBestActions(many).length).toBe(5);
  });

  it('for a technician keeps only their own assigned items', () => {
    const out = rankNextBestActions({ ...base, role: 'TECHNICIEN' });
    // urgent WO #10 is assigned to tech 2 -> excluded; WO #11 is MOYENNE -> not urgent
    const woKeys = out.filter((a) => a.key.startsWith('wo-')).map((a) => a.key);
    expect(woKeys).toEqual([]);
  });

  it('keeps a technician-owned urgent WO', () => {
    const out = rankNextBestActions({
      ...base,
      role: 'TECHNICIEN',
      workOrders: [{ id: 12, priorite: 'URGENTE', statut: 'EN_ATTENTE', technicien_id: 1 }],
    });
    expect(out.filter((a) => a.key.startsWith('wo-')).map((a) => a.key)).toEqual(['wo-12']);
  });

  it('builds a drill-through href per action', () => {
    const out = rankNextBestActions(base);
    const alert = out.find((a) => a.severity === 'critical');
    expect(alert.href).toContain('/machines/7');
  });

  it('returns empty for empty input', () => {
    expect(rankNextBestActions({ role: 'ADMIN', workOrders: [], overduePMs: [], alerts: [] }))
      .toEqual([]);
  });
});
