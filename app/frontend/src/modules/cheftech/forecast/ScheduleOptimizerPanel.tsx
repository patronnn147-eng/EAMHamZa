import { useState } from 'react';
import { Calendar, RefreshCw, AlertTriangle, Info } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface Assignment {
  wo_id: number;
  titre: string;
  technician_id: number;
  start_day: number;
  end_day: number;
}

interface ScheduleResult {
  assignments: Assignment[];
  makespan_days: number;
  solved: boolean;
  fallback: boolean;
}

interface Props { horizon: number }

export function ScheduleOptimizerPanel({ horizon }: Readonly<Props>) {
  const [result, setResult] = useState<ScheduleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOptimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/v1/ml/forecast/optimize-schedule?horizon=${horizon}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!r.ok) throw new Error(`Erreur ${r.status}`);
      setResult(await r.json());
    } catch (e: any) {
      setError(e.message ?? 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Optimiseur de planning</p>
        <button
          onClick={handleOptimize}
          disabled={loading}
          className="inline-flex items-center gap-2 text-xs font-medium text-blue-200 bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 hover:bg-slate-700/60 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Optimisation…' : 'Optimiser le planning'}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded bg-red-950 border border-red-800 px-3 py-2 text-xs text-red-300">
          <AlertTriangle className="h-3.5 w-3.5" /> {error}
        </div>
      )}

      {result && (
        <div className="space-y-2">
          {result.fallback && (
            <div className="flex items-center gap-2 rounded bg-amber-950 border border-amber-800 px-3 py-2 text-xs text-amber-300">
              <Info className="h-3.5 w-3.5" /> Mode simplifié — solveur OR-Tools non disponible.
            </div>
          )}
          {!result.solved && (
            <div className="flex items-center gap-2 rounded bg-amber-950 border border-amber-800 px-3 py-2 text-xs text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5" /> Solution partielle — délai de résolution dépassé.
            </div>
          )}
          <p className="text-xs text-slate-400">
            {result.assignments.length} ordre(s) planifié(s) · Durée totale : {result.makespan_days}j
          </p>
          <div className="rounded-lg border border-slate-700 overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-800 text-blue-300">
                <tr>
                  <th className="text-left px-3 py-2">Ordre</th>
                  <th className="text-left px-3 py-2">Technicien</th>
                  <th className="text-left px-3 py-2">Début (J)</th>
                  <th className="text-left px-3 py-2">Fin (J)</th>
                </tr>
              </thead>
              <tbody>
                {result.assignments.map(a => (
                  <tr key={a.wo_id} className="border-t border-slate-800">
                    <td className="px-3 py-2 text-slate-200">{a.titre || `OT #${a.wo_id}`}</td>
                    <td className="px-3 py-2 text-slate-300">#{a.technician_id}</td>
                    <td className="px-3 py-2 text-slate-300">J+{a.start_day}</td>
                    <td className="px-3 py-2 text-slate-300">J+{a.end_day}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!result && !loading && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Calendar className="h-4 w-4" />
          Cliquez sur "Optimiser" pour répartir les ordres de travail ouverts entre les techniciens.
        </div>
      )}
    </div>
  );
}
