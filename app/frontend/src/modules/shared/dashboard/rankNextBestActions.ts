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

function getMachineImpact(machineId: number | null | undefined, crit: Record<number, number>): number {
  return (machineId != null && crit[machineId]) ? crit[machineId] : 1;
}

function collectAlertActions(
  alerts: NbaAlert[],
  isTech: boolean,
  crit: Record<number, number>,
): RankedAction[] {
  const actions: RankedAction[] = [];
  for (const a of alerts) {
    if ((a.severity ?? '').toUpperCase() !== 'CRITICAL') continue;
    if (isTech) continue;
    const machineSuffix = a.machine_id ? ` — machine ${a.machine_id}` : '';
    actions.push({
      key: `alert-${a.machine_id ?? 'x'}`,
      label: `Alerte critique${machineSuffix}`,
      severity: 'critical',
      href: a.machine_id == null ? '/machines' : `/machines/${a.machine_id}`,
      score: URGENCY.criticalAlert * getMachineImpact(a.machine_id, crit),
    });
  }
  return actions;
}

function collectWorkOrderActions(
  workOrders: NbaWorkOrder[],
  isTech: boolean,
  userId: number | undefined,
  crit: Record<number, number>,
): RankedAction[] {
  const actions: RankedAction[] = [];
  for (const wo of workOrders) {
    if (wo.priorite !== 'URGENTE' || wo.statut === 'TERMINE') continue;
    if (isTech && wo.technicien_id !== userId) continue;
    actions.push({
      key: `wo-${wo.id}`,
      label: `Ordre urgent #${wo.id}`,
      severity: 'high',
      href: `/work-orders?id=${wo.id}`,
      score: URGENCY.urgentWo * getMachineImpact(wo.machine_id, crit),
    });
  }
  return actions;
}

function collectPmActions(overduePMs: NbaPM[], crit: Record<number, number>): RankedAction[] {
  return overduePMs.map(pm => ({
    key: `pm-${pm.machine_id}`,
    label: `Maintenance en retard — ${pm.nom}`,
    severity: 'medium' as const,
    href: `/planning?machine=${pm.machine_id}`,
    score: URGENCY.overduePm * getMachineImpact(pm.machine_id, crit),
  }));
}

export function rankNextBestActions(input: NbaInput): RankedAction[] {
  const isTech = input.role === 'TECHNICIEN';
  const crit = input.machineCriticality ?? {};

  const actions: RankedAction[] = [
    ...collectAlertActions(input.alerts, isTech, crit),
    ...collectWorkOrderActions(input.workOrders, isTech, input.userId, crit),
    ...collectPmActions(input.overduePMs, crit),
  ];

  actions.sort((a, b) => b.score - a.score);
  return actions.slice(0, 5);
}
