import { useEffect, useState } from 'react';
import { TrendingDown, Clock } from 'lucide-react';
import { formatHours } from '@/modules/cheftech/forecast/forecastTransforms';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface MachineDowntime {
  machine_id: number;
  machine_name: string;
  p_failure: number;
  expected_downtime_hours: number;
  horizon_days: number;
}

interface Props { machineId: number }

export function MachineForecastPanel({ machineId }: Props) {
  const [data, setData] = useState<MachineDowntime | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/v1/ml/forecast/downtime?horizon=30`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(j => {
        if (!j) return;
        const machine = j.machines?.find((m: MachineDowntime) => m.machine_id === machineId);
        if (machine) setData(machine);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [machineId]);

  if (loading) return <div className="h-28 rounded-lg bg-slate-800 animate-pulse" />;
  if (!data) return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/40 px-4 py-3 text-xs text-slate-400">
      Données de prévision non disponibles.
    </div>
  );

  const pct = Math.round(data.p_failure * 100);
  const riskColor = pct >= 70 ? 'text-red-400' : pct >= 40 ? 'text-amber-400' : 'text-emerald-400';

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/60 p-4 space-y-3">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Prévision 30 jours</p>
      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-start gap-2">
          <TrendingDown className="h-4 w-4 text-red-400 mt-0.5" />
          <div>
            <p className="text-xs text-slate-400">Probabilité de panne</p>
            <p className={`text-xl font-bold mt-0.5 ${riskColor}`}>{pct}%</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Clock className="h-4 w-4 text-amber-400 mt-0.5" />
          <div>
            <p className="text-xs text-slate-400">Arrêt attendu</p>
            <p className="text-xl font-bold text-slate-100 mt-0.5">{formatHours(data.expected_downtime_hours)}</p>
          </div>
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-slate-700">
        <div
          className={`h-1.5 rounded-full ${pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
