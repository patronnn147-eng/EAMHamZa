import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { DowntimeForecastChart } from './DowntimeForecastChart';
import { LaborForecastChart } from './LaborForecastChart';
import { BudgetForecastCard } from './BudgetForecastCard';
import { ScheduleOptimizerPanel } from './ScheduleOptimizerPanel';
import { TechnicianScheduleView } from './TechnicianScheduleView';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

type Horizon = 7 | 30 | 60;

function useApi<T>(path: string, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token()}` } })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setData(j))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, deps);
  return { data, loading };
}

export default function ForecastDashboard() {
  const { user } = useAuth();
  const role = (user as any)?.role ?? '';
  const isTech = role === 'TECHNICIEN';
  const [horizon, setHorizon] = useState<Horizon>(30);

  const downtime = useApi<any>(`/api/v1/ml/forecast/downtime?horizon=${horizon}`, [horizon]);
  const labor = useApi<any>(`/api/v1/ml/forecast/labor?horizon=${horizon}`, [horizon]);
  const budget = useApi<any>(`/api/v1/ml/forecast/budget?horizon=${horizon}`, [horizon]);

  if (isTech) return <TechnicianScheduleView />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">Prévisions & Optimisation</h2>
          <p className="text-sm text-blue-300 mt-1">Horizon court terme — arrêts, charge, budget.</p>
        </div>
        <div className="flex rounded-lg border border-slate-700 overflow-hidden">
          {([7, 30, 60] as Horizon[]).map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                horizon === h
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {h}j
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          {downtime.loading
            ? <div className="h-52 animate-pulse bg-slate-800 rounded" />
            : downtime.data && <DowntimeForecastChart machines={downtime.data.machines ?? []} />}
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          {labor.loading
            ? <div className="h-52 animate-pulse bg-slate-800 rounded" />
            : labor.data && <LaborForecastChart data={labor.data} horizon={horizon} />}
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          {budget.loading
            ? <div className="h-40 animate-pulse bg-slate-800 rounded" />
            : budget.data && <BudgetForecastCard data={budget.data} />}
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          <ScheduleOptimizerPanel horizon={horizon} />
        </div>
      </div>
    </div>
  );
}
