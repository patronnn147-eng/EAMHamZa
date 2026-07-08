export interface NbaWorkOrder {
  id: number;
  priorite: string;
  statut: string;
  technicien_id?: number | null;
  machine_id?: number | null;
}
export interface NbaPM { machine_id: number; nom: string }
export interface NbaAlert { type: string; severity?: string; machine_id?: number | null }

export interface NbaInput {
  role: string;
  userId?: number;
  workOrders: NbaWorkOrder[];
  overduePMs: NbaPM[];
  alerts: NbaAlert[];
  machineCriticality?: Record<number, number>;
}

export interface RankedAction {
  key: string;
  label: string;
  severity: 'critical' | 'high' | 'medium';
  href: string;
  score: number;
}

const URGENCY = { criticalAlert: 100, urgentWo: 70, overduePm: 40 };

export function rankNextBestActions(input: NbaInput): RankedAction[] {
  const isTech = input.role === 'TECHNICIEN';
  const crit = input.machineCriticality ?? {};
  const impact = (machineId?: number | null) =>
    (machineId != null && crit[machineId]) ? crit[machineId] : 1;

  const actions: RankedAction[] = [];

  for (const a of input.alerts) {
    if ((a.severity ?? '').toUpperCase() !== 'CRITICAL') continue;
    if (isTech) continue; // techs act on their WOs, managers triage alerts
    const machineSuffix = a.machine_id ? ` — machine ${a.machine_id}` : '';
    actions.push({
      key: `alert-${a.machine_id ?? 'x'}`,
      label: `Alerte critique${machineSuffix}`,
      severity: 'critical',
      href: a.machine_id != null ? `/machines/${a.machine_id}` : '/machines',
      score: URGENCY.criticalAlert * impact(a.machine_id),
    });
  }

  for (const wo of input.workOrders) {
    if (wo.priorite !== 'URGENTE' || wo.statut === 'TERMINE') continue;
    if (isTech && wo.technicien_id !== input.userId) continue;
    actions.push({
      key: `wo-${wo.id}`,
      label: `Ordre urgent #${wo.id}`,
      severity: 'high',
      href: `/work-orders?id=${wo.id}`,
      score: URGENCY.urgentWo * impact(wo.machine_id),
    });
  }

  for (const pm of input.overduePMs) {
    actions.push({
      key: `pm-${pm.machine_id}`,
      label: `Maintenance en retard — ${pm.nom}`,
      severity: 'medium',
      href: `/planning?machine=${pm.machine_id}`,
      score: URGENCY.overduePm * impact(pm.machine_id),
    });
  }

  actions.sort((a, b) => b.score - a.score);
  return actions.slice(0, 5);
}
