import type { WhyPayload, WhyReason } from '../whyTypes';
import type { UnifiedHealthLike } from './buildHealthWhy';

export function buildAnomalyWhy(health: UnifiedHealthLike): WhyPayload {
  const sensors = health.sensor_status ?? [];
  const abnormal = sensors.filter((s) => s.status !== 'NORMAL');
  const reasons: WhyReason[] = abnormal.map((s) => ({
    label: `${s.label} se comporte de façon inhabituelle`,
    detail: `actuellement ${s.value} ${s.unit}`,
    tone: s.status === 'CRITIQUE' ? 'critical' : 'warning',
  }));

  // When nothing is out of the ordinary the panel used to be blank, which left
  // the explain button with nothing to send and made a normal machine look like
  // a broken screen. State what was actually checked instead.
  if (!reasons.length && sensors.length) {
    reasons.push({
      label: `${sensors.length} mesures vérifiées, toutes dans leur plage habituelle`,
      detail: sensors.map((s) => s.label).join(', '),
      tone: 'normal',
    });
  }

  return {
    title: health.is_anomaly ? 'Comportement inhabituel détecté' : 'Comportement normal',
    summary: abnormal.length
      ? 'Un ou plusieurs capteurs s’écartent de leur fonctionnement habituel.'
      : 'Les capteurs fonctionnent comme d’habitude.',
    reasons,
    source: 'Comparé au fonctionnement habituel de ce type de machine.',
    llmContext: { reasons: reasons.map((r) => r.label) },
  };
}
