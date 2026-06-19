import type { WhyPayload, WhyReason } from '../whyTypes';
import type { UnifiedHealthLike } from './buildHealthWhy';

export function buildAnomalyWhy(health: UnifiedHealthLike): WhyPayload {
  const abnormal = (health.sensor_status ?? []).filter((s) => s.status !== 'NORMAL');
  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} se comporte de façon inhabituelle`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: s.status === 'CRITIQUE' ? 'critical' : 'warning',
  }));
  return {
    title: health.is_anomaly ? 'Comportement inhabituel détecté' : 'Comportement normal',
    summary: reasons.length
      ? 'Un ou plusieurs capteurs s’écartent de leur fonctionnement habituel.'
      : 'Les capteurs fonctionnent comme d’habitude.',
    reasons,
    source: 'Comparé au fonctionnement habituel de ce type de machine.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
