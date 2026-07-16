import type { WhyPayload, WhyReason, WhyTone } from '../whyTypes';
import { confidenceWords } from '../plainLanguage';

export interface SensorStatus {
  key: string; label: string; value: number; unit: string;
  status: 'NORMAL' | 'ATTENTION' | 'CRITIQUE'; target: number | null;
}
export interface UnifiedHealthLike {
  dst_verdict?: string;
  conflict_factor_K?: number;
  is_anomaly?: boolean;
  sensor_status?: SensorStatus[];
  explanations?: { factor: string; impact: number; intensity: string }[];
}

const VERDICT_TITLE: Record<string, string> = {
  Critical: 'Risque de panne élevé',
  Degrading: 'État qui se dégrade',
  Healthy: 'Machine en bon état',
};
const toneOf = (s: string): WhyTone => {
  if (s === 'CRITIQUE') return 'critical';
  if (s === 'ATTENTION') return 'warning';
  return 'normal';
};

export function buildHealthWhy(health: UnifiedHealthLike): WhyPayload {
  const sensors = health.sensor_status ?? [];
  const abnormal = sensors.filter((s) => s.status !== 'NORMAL');
  const title = VERDICT_TITLE[health.dst_verdict ?? ''] ?? 'État de la machine';

  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} ${s.value > (s.target ?? Infinity) ? 'trop élevé' : 'hors de la plage sûre'}`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: toneOf(s.status),
  }));

  const counterfactual: WhyReason[] = abnormal
    .filter((s) => s.target != null)
    .map((s) => ({
      label: `Ramener ${s.label.toLowerCase()} sous ${s.target} ${s.unit}`,
      detail: `actuellement ${s.value} ${s.unit}`,
      tone: 'normal',
    }));

  const confidence = health.conflict_factor_K == null
    ? undefined : confidenceWords(health.conflict_factor_K);

  const summary = abnormal.length
    ? `Principale raison : ${abnormal[0].label.toLowerCase()} hors de la plage sûre.`
    : 'Aucun signal préoccupant pour le moment.';

  return {
    title, summary, reasons,
    confidence,
    counterfactual: counterfactual.length ? counterfactual : undefined,
    source: 'Basé sur les dernières mesures des capteurs et l’historique de pannes.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
