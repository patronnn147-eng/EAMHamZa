import { useEffect, useState } from 'react';
import { Calendar, Info } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface Assignment {
  wo_id: number;
  titre: string;
  start_day: number;
  end_day: number;
}

interface MySchedule {
  assignments: Assignment[];
  technician_id: number;
  solved: boolean;
  fallback: boolean;
}

export function TechnicianScheduleView() {
  const [data, setData] = useState<MySchedule | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/ml/forecast/my-schedule`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setData(j))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-40 rounded-lg bg-slate-800 animate-pulse" />;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-white">Mon planning</h2>
        <p className="text-sm text-blue-300 mt-1">Ordres de travail qui vous sont assignés (30 jours)</p>
      </div>

      {data?.fallback && (
        <div className="flex items-center gap-2 rounded bg-slate-800 border border-slate-700 px-3 py-2 text-xs text-slate-400">
          <Info className="h-3.5 w-3.5" /> Planning généré en mode simplifié.
        </div>
      )}

      {!data || data.assignments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-2">
          <Calendar className="h-8 w-8" />
          <p className="text-sm">Aucun ordre de travail planifié pour le moment.</p>
          <p className="text-xs text-slate-500">Votre chef technique doit d'abord lancer l'optimisation du planning.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-blue-300 text-xs">
              <tr>
                <th className="text-left px-4 py-2">Ordre de travail</th>
                <th className="text-left px-4 py-2">Début prévu</th>
                <th className="text-left px-4 py-2">Fin prévue</th>
                <th className="text-left px-4 py-2">Durée</th>
              </tr>
            </thead>
            <tbody>
              {data.assignments.map(a => (
                <tr key={a.wo_id} className="border-t border-slate-800">
                  <td className="px-4 py-3 text-slate-100 font-medium">{a.titre || `OT #${a.wo_id}`}</td>
                  <td className="px-4 py-3 text-slate-300">J+{a.start_day}</td>
                  <td className="px-4 py-3 text-slate-300">J+{a.end_day}</td>
                  <td className="px-4 py-3 text-slate-300">{a.end_day - a.start_day}j</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
