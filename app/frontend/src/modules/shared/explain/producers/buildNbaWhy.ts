import type { WhyPayload } from '../whyTypes';
import type { RankedAction } from '../../dashboard/rankNextBestActions';

const WHY: Record<string, string> = {
  critical: 'Risque immédiat — à traiter en priorité.',
  high: 'Urgent — à planifier aujourd’hui.',
  medium: 'À prévoir bientôt pour éviter un arrêt.',
};

export function buildNbaWhy(action: RankedAction): WhyPayload {
  let actionTone: 'critical' | 'warning' | 'normal';
  if (action.severity === 'critical') {
    actionTone = 'critical';
  } else if (action.severity === 'high') {
    actionTone = 'warning';
  } else {
    actionTone = 'normal';
  }

  return {
    title: 'Pourquoi cette action ?',
    summary: WHY[action.severity] ?? 'Action recommandée.',
    reasons: [
      { label: action.label, tone: actionTone },
      { label: WHY[action.severity] ?? 'Recommandé', tone: 'info' },
    ],
    source: 'Classé par urgence et impact sur la production.',
    llmContext: { reasons: [action.label, WHY[action.severity] ?? ''] },
  };
}
