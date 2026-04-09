import React from 'react';
import { Badge } from '@/components/ui/badge';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';

interface AnomalyAlertsProps {
  isAnomaly: boolean;
  anomalyScore: number;
}

export const AnomalyAlerts: React.FC<AnomalyAlertsProps> = ({ isAnomaly, anomalyScore }) => {
  if (!isAnomaly) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 border border-emerald-100">
        <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-emerald-700">Aucune anomalie détectée</p>
          <p className="text-xs text-emerald-600 mt-0.5">
            Tous les capteurs fonctionnent normalement. Score d'anomalie: {anomalyScore.toFixed(4)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-purple-50 border border-purple-200">
      <ShieldAlert className="h-5 w-5 text-purple-600 shrink-0 mt-0.5" />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <Badge variant="destructive" className="bg-purple-600 animate-pulse">
            ⚠️ Anomalie Détectée
          </Badge>
        </div>
        <p className="text-sm text-purple-700 mt-2">
          Score d'anomalie: <span className="font-bold">{anomalyScore.toFixed(4)}</span> — Les capteurs montrent un comportement anormal.
        </p>
        <p className="text-xs text-purple-600 mt-1">
          Une inspection technique est recommandée pour identifier la cause racine.
        </p>
      </div>
    </div>
  );
};
