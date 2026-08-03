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

/** Share of its limit a reading has consumed, or null when there is no limit. */
export const limitRatio = (s: SensorStatus): number | null =>
  s.target == null || s.target === 0 ? null : s.value / s.target;

/** "Couple à 55.4 Nm, limite 60 Nm" — the machine's condition, in numbers. */
export const readingPhrase = (s: SensorStatus): string =>
  s.target == null
    ? `${s.label} à ${s.value} ${s.unit}`
    : `${s.label} à ${s.value} ${s.unit}, limite ${s.target} ${s.unit}`;

/** Sensors closest to their limit first — the ones worth telling an operator about. */
export const byClosestToLimit = (sensors: SensorStatus[]): SensorStatus[] =>
  sensors
    .filter((s) => limitRatio(s) != null)
    .sort((a, b) => (limitRatio(b) as number) - (limitRatio(a) as number));

/** Match a model factor name back to the sensor it refers to, so the reason can
 *  carry a real reading instead of an abstract statement. */
export const sensorForFactor = (factor: string, sensors: SensorStatus[]): SensorStatus | undefined => {
  // Model factor names and sensor labels describe the same thing in different
  // words ("Usure de l'Outil" vs "Usure outil"), so compare the meaningful
  // words rather than the whole string.
  const STOP = new Set(['de', 'du', 'la', 'le', 'les', 'l', 'd', 'des', 'en']);
  const words = (v: string) =>
    new Set(
      v.toLowerCase()
        .normalize('NFD').replace(/[̀-ͯ]/g, '')
        .split(/[^a-z0-9]+/)
        .filter((w) => w.length > 1 && !STOP.has(w)),
    );

  const f = words(factor);
  if (!f.size) return undefined;

  let best: SensorStatus | undefined;
  let bestScore = 0;
  for (const s of sensors) {
    const cand = new Set([...words(s.label), ...words(s.key)]);
    let hits = 0;
    f.forEach((w) => { if (cand.has(w)) hits += 1; });
    const score = hits / f.size;
    if (score > bestScore) { bestScore = score; best = s; }
  }
  // Require a real overlap: "temp_delta" is derived and matches no sensor.
  return bestScore >= 0.5 ? best : undefined;
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
      const s = sensorForFactor(e.factor, sensors);
      const ratio = s ? limitRatio(s) : null;
      reasons.push({
        // Name the reading and where it actually stands, not the fact that a
        // check ran. An operator needs the machine's condition, not ours.
        label: s ? readingPhrase(s) : prettyFactor(e.factor),
        detail: ratio != null
          ? `${Math.round(ratio * 100)} % de la limite — sous le seuil, mais en évolution défavorable`
          : "s'écarte du comportement habituel de cette machine",
        tone: e.intensity === 'high' ? 'warning' : 'normal',
      });
    }

    const drifting = byClosestToLimit(sensors).filter((s) => (limitRatio(s) as number) >= 0.85);
    if (drifting.length >= 2) {
      reasons.push({
        label: `${drifting.length} mesures dépassent 85 % de leur limite en même temps`,
        detail: drifting
          .map((s) => `${s.label} ${Math.round((limitRatio(s) as number) * 100)} %`)
          .join(' · '),
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
    // Send the detail too — it carries the numbers, so the plain-language
    // paragraph can talk about the machine rather than about the checks.
    llmContext: { reasons: reasons.map((r) => (r.detail ? `${r.label} (${r.detail})` : r.label)) },
  };
}
