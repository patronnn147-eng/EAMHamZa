import { useEffect, useState } from 'react';
import { TrendingDown, Clock, Banknote, AlertTriangle } from 'lucide-react';
import { formatHours, formatCurrency } from '@/modules/cheftech/forecast/forecastTransforms';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface ForecastSummary {
  downtime_hours: number;
  labor_demand_hours: number;
  labor_overload: boolean;
  budget_total: number;
  currency: string;
}

export function ForecastSummaryTile() {
  const [data, setData] = useState<ForecastSummary | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/ml/forecast/summary`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setData(j))
      .catch(() => {});
  }, []);

  if (!data) return <div className="h-20 rounded-lg bg-slate-800 animate-pulse col-span-3" />;

  const tiles = [
    {
      icon: <TrendingDown className="h-4 w-4 text-red-400" />,
      label: "Temps d'arrêt prévu (30j)",
      value: formatHours(data.downtime_hours),
      accent: data.downtime_hours > 40 ? 'text-red-300' : 'text-slate-100',
      badge: null as React.ReactNode,
    },
    {
      icon: <Clock className="h-4 w-4 text-amber-400" />,
      label: "Main-d'œuvre requise (30j)",
      value: formatHours(data.labor_demand_hours),
      accent: data.labor_overload ? 'text-amber-300' : 'text-slate-100',
      badge: data.labor_overload ? (
        <span className="ml-2 inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-900/40 rounded px-1.5 py-0.5">
          <AlertTriangle className="h-3 w-3" /> Surcharge
        </span>
      ) : null as React.ReactNode,
    },
    {
      icon: <Banknote className="h-4 w-4 text-blue-400" />,
      label: 'Budget maintenance estimé',
      value: formatCurrency(data.budget_total),
      accent: 'text-slate-100',
      badge: null as React.ReactNode,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {tiles.map(t => (
        <div key={t.label} className="rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 flex items-start gap-3">
          <div className="mt-0.5">{t.icon}</div>
          <div>
            <p className="text-xs text-slate-400">{t.label}</p>
            <p className={`text-lg font-semibold mt-0.5 ${t.accent}`}>
              {t.value}{t.badge}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
