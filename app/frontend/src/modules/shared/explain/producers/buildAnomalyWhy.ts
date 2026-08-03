import type { WhyPayload, WhyReason } from '../whyTypes';
import type { UnifiedHealthLike } from './buildHealthWhy';
import { byClosestToLimit, limitRatio, readingPhrase } from './buildHealthWhy';

export function buildAnomalyWhy(health: UnifiedHealthLike): WhyPayload {
  const sensors = health.sensor_status ?? [];
  const abnormal = sensors.filter((s) => s.status !== 'NORMAL');
  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} se comporte de façon inhabituelle`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: s.status === 'CRITIQUE' ? 'critical' : 'warning',
  }));

  // Nothing is out of range, but "we checked 5 things" describes our own
  // verification rather than the machine. Report where the machine actually
  // stands instead: the readings closest to their limit, with real values.
  // Those are what an operator would want to watch next.
  const closest = byClosestToLimit(sensors).slice(0, 3);
  if (!reasons.length && closest.length) {
    for (const s of closest) {
      const pct = Math.round((limitRatio(s) as number) * 100);
      reasons.push({
        label: readingPhrase(s),
        detail: `${pct} % de sa limite${pct >= 85 ? ' — à surveiller' : ''}`,
        tone: pct >= 85 ? 'warning' : 'normal',
      });
    }
  }

  let summary: string;
  if (abnormal.length) {
    summary = 'Un ou plusieurs capteurs s’écartent de leur fonctionnement habituel.';
  } else if (closest.length) {
    const top = closest[0];
    summary = `Aucune mesure ne dépasse sa limite. La plus proche est ${top.label.toLowerCase()}, `
      + `à ${Math.round((limitRatio(top) as number) * 100)} % de sa limite.`;
  } else {
    summary = 'Les capteurs fonctionnent comme d’habitude.';
  }

  return {
    title: health.is_anomaly ? 'Comportement inhabituel détecté' : 'Comportement normal',
    summary,
    reasons,
    source: 'Comparé au fonctionnement habituel de ce type de machine.',
    llmContext: { reasons: reasons.map((r) => `${r.label} (${r.detail})`) },
  };
}
