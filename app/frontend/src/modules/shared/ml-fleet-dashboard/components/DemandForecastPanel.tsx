import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PackageOpen, RefreshCw, CheckCircle2, AlertTriangle, Clock } from 'lucide-react';
import { useInventoryForecast } from '../hooks/useInventoryForecast';
import type { ForecastItem } from '../hooks/useInventoryForecast';

const urgencyConfig = {
  URGENT: {
    label: 'Urgent',
    badgeClass: 'bg-red-100 text-red-700 border-red-200',
    cardBorder: 'border-l-red-500',
    icon: <AlertTriangle className="h-3.5 w-3.5 text-red-500" />,
  },
  SOON: {
    label: 'Bientôt',
    badgeClass: 'bg-amber-100 text-amber-700 border-amber-200',
    cardBorder: 'border-l-amber-400',
    icon: <Clock className="h-3.5 w-3.5 text-amber-500" />,
  },
  MONITOR: {
    label: 'À surveiller',
    badgeClass: 'bg-slate-100 text-slate-600 border-slate-200',
    cardBorder: 'border-l-slate-400',
    icon: <PackageOpen className="h-3.5 w-3.5 text-slate-400" />,
  },
};

function ForecastItemCard({ item }: Readonly<{ item: ForecastItem }>) {
  const cfg = urgencyConfig[item.urgency_label] || urgencyConfig.MONITOR;
  const isEstimated = item.consumption_data === 'estimated';

  return (
    <Card className={`border-l-4 ${cfg.cardBorder} shadow-sm`}>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-white truncate">{item.piece_name}</p>
            <p className="text-xs text-blue-300 mt-0.5">
              Stock actuel: <span className="font-bold text-white">{item.current_qty}</span>
              {' · '}
              À commander:{' '}
              <span className="font-bold text-white">
                {isEstimated ? '~' : ''}{item.reorder_qty_suggested}
              </span>
              {isEstimated && (
                <span
                  className="ml-1 cursor-help underline decoration-dotted"
                  title="Basé sur une estimation — aucun historique de consommation disponible"
                >
                  (estimé)
                </span>
              )}
            </p>
          </div>
          <Badge className={`shrink-0 text-[10px] px-1.5 py-0 border ${cfg.badgeClass}`}>
            {cfg.label}
          </Badge>
        </div>

        {/* Machines affected */}
        {item.machines_affected.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {item.machines_affected.slice(0, 3).map((m) => (
              <span
                key={m.id}
                className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                  m.rul_days <= 14 ? 'bg-red-900/40 text-red-300' : 'bg-slate-800 text-blue-300'
                }`}
              >
                {m.name} ({Math.round(m.rul_days)}j)
              </span>
            ))}
            {item.machines_affected.length > 3 && (
              <span className="text-[10px] text-blue-400 px-1 py-0.5">
                +{item.machines_affected.length - 3} de plus
              </span>
            )}
          </div>
        )}

        {/* Stockout warning */}
        {item.days_until_stockout !== null && item.days_until_stockout <= 30 && (
          <p className="text-[10px] text-red-400 font-mono">
            ⚠ Rupture estimée dans ~{item.days_until_stockout} jour{item.days_until_stockout === 1 ? '' : 's'}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function DemandForecastPanel() {
  const { data, loading, error, refresh } = useInventoryForecast(60, 20);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <PackageOpen className="h-5 w-5 text-blue-400" />
            Prévisions de Réapprovisionnement
          </h2>
          <p className="text-xs text-blue-300 mt-0.5">
            Horizon 60 jours · Croisement RUL × Stock × Consommation
            {data && (
              <>
                {' '}·{' '}
                <span className="text-red-400 font-semibold">{data.total_urgent} urgent</span>
                {' · '}
                <span className="text-blue-300">{data.total_monitor} à surveiller</span>
              </>
            )}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={refresh}
          disabled={loading}
          className="shrink-0"
        >
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </Button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-lg bg-slate-800/60 animate-pulse border-l-4 border-l-slate-700" />
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <Card className="border-red-800">
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-red-400">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!loading && !error && data?.items.length === 0 && (
        <Card>
          <CardContent className="pt-8 pb-8 text-center">
            <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto mb-3" />
            <p className="text-sm font-semibold text-emerald-400">Aucun réapprovisionnement nécessaire</p>
            <p className="text-xs text-blue-300 mt-1">Toutes les pièces sont suffisamment stockées pour les 60 prochains jours.</p>
          </CardContent>
        </Card>
      )}

      {/* Forecast list */}
      {!loading && !error && data?.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((item) => (
            <ForecastItemCard key={item.piece_id} item={item} />
          ))}
          <p className="text-[10px] text-blue-400 text-right font-mono">
            Généré le {new Date(data.generated_at).toLocaleString('fr-FR')} · Cache 1h
          </p>
        </div>
      )}
    </div>
  );
}
