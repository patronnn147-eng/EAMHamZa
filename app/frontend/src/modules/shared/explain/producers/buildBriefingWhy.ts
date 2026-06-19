import type { WhyPayload, WhyReason } from '../whyTypes';

export interface BriefingFacts {
  urgent_wos: number;
  overdue_pms: number;
  degraded_machines: string[];
  active_alerts: number;
}

export function buildBriefingWhy(facts: BriefingFacts): WhyPayload {
  const reasons: WhyReason[] = [];
  if (facts.urgent_wos) reasons.push({ label: `${facts.urgent_wos} intervention(s) urgente(s)`, tone: 'critical' });
  if (facts.degraded_machines?.length) reasons.push({ label: `Machines à surveiller : ${facts.degraded_machines.slice(0, 3).join(', ')}`, tone: 'warning' });
  if (facts.overdue_pms) reasons.push({ label: `${facts.overdue_pms} entretien(s) en retard`, tone: 'warning' });
  if (facts.active_alerts) reasons.push({ label: `${facts.active_alerts} alerte(s) en cours`, tone: 'warning' });
  return {
    title: 'Pourquoi ce résumé ?',
    summary: reasons.length ? 'Voici ce qui demande votre attention aujourd’hui.' : 'Rien d’urgent aujourd’hui.',
    reasons,
    source: 'Résumé des interventions, entretiens et alertes du jour.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
