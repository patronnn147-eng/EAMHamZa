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

// Factor keys the models emit are not all human-readable.
const FACTOR_LABEL: Record<string, string> = {
  temp_delta: 'Écart entre température procédé et température air',
  air_temperature: 'Température air',
  process_temperature: 'Température procédé',
  rotational_speed: 'Vitesse de rotation',
  torque: 'Couple',
  tool_wear: 'Usure outil',
};
const prettyFactor = (f: string) => FACTOR_LABEL[f] ?? f.replace(/_/g, ' ');

export function buildHealthWhy(health: UnifiedHealthLike): WhyPayload {
  const sensors = health.sensor_status ?? [];
  const abnormal = sensors.filter((s) => s.status !== 'NORMAL');
  const title = VERDICT_TITLE[health.dst_verdict ?? ''] ?? 'État de la machine';

  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} ${s.value > (s.target ?? Infinity) ? 'trop élevé' : 'hors de la plage sûre'}`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: toneOf(s.status),
  }));

  // A machine can be judged at risk while every single sensor still reads
  // inside its own safe band: the verdict also weighs how the readings move
  // together and how far they drift from this machine's own normal. Without
  // this fallback the panel says "nothing concerning" under a title that says
  // the opposite, which is exactly the case operators lose trust over.
  if (!reasons.length) {
    const flagged = (health.explanations ?? [])
      .filter((e) => e.intensity === 'high' || e.intensity === 'medium')
      .slice(0, 3);

    for (const e of flagged) {
      reasons.push({
        label: `${prettyFactor(e.factor)} : évolution inhabituelle`,
        detail: "cette mesure reste dans sa plage, mais s'écarte du comportement habituel de cette machine",
        tone: e.intensity === 'high' ? 'warning' : 'normal',
      });
    }

    const drifting = sensors
      .filter((s) => s.target != null && s.value >= 0.85 * (s.target as number))
      .map((s) => s.label);
    if (drifting.length >= 2) {
      reasons.push({
        label: `Plusieurs mesures approchent leur limite en même temps`,
        detail: drifting.join(', '),
        tone: 'warning',
      });
    }

    if (!reasons.length && (health.dst_verdict === 'Critical' || health.dst_verdict === 'Degrading')) {
      reasons.push({
        label: 'Tendance générale défavorable',
        detail: "aucune mesure isolée n'est hors plage, mais leur évolution combinée est surveillée",
        tone: 'normal',
      });
    }
  }

  const counterfactual: WhyReason[] = abnormal
    .filter((s) => s.target != null)
    .map((s) => ({
      label: `Ramener ${s.label.toLowerCase()} sous ${s.target} ${s.unit}`,
      detail: `actuellement ${s.value} ${s.unit}`,
      tone: 'normal',
    }));

  const confidence = health.conflict_factor_K == null
    ? undefined : confidenceWords(health.conflict_factor_K);

  let summary: string;
  if (abnormal.length) {
    summary = `Principale raison : ${abnormal[0].label.toLowerCase()} hors de la plage sûre.`;
  } else if (reasons.length) {
    // Don't claim "nothing concerning" under a title that says the opposite.
    summary = 'Aucune mesure n’est hors plage, mais leur évolution combinée justifie une surveillance.';
  } else {
    summary = 'Aucun signal préoccupant pour le moment.';
  }

  return {
    title, summary, reasons,
    confidence,
    counterfactual: counterfactual.length ? counterfactual : undefined,
    source: 'Basé sur les dernières mesures des capteurs et l’historique de pannes.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
