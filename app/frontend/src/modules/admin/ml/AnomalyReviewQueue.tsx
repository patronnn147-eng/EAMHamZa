import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, CheckCircle, XCircle, HelpCircle } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface SensorSnapshot {
  air_temperature: number | null;
  process_temperature: number | null;
  rotational_speed: number | null;
  torque: number | null;
  tool_wear: number | null;
}
interface AnomalyFlag {
  id: number;
  machine_id: number;
  machine_name: string | null;
  anomaly_score: number | null;
  sensor_snapshot: SensorSnapshot;
  flagged_at: string | null;
}
interface Queue { pending_count: number; items: AnomalyFlag[] }

function formatAgo(iso: string | null): string {
  if (!iso) return '—';
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 3600000);
  if (d < 1) return "à l'instant";
  if (d < 24) return `il y a ${d} h`;
  return `il y a ${Math.floor(d / 24)} j`;
}

export function AnomalyReviewQueue() {
  const [q, setQ] = useState<Queue | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = async () => {
    try {
      const r = await fetch(`${API}/api/v1/ml/anomaly-review/queue?limit=20`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (r.ok) setQ(await r.json());
    } catch { /* leave null */ }
  };
  useEffect(() => { load(); }, []);

  const submit = async (id: number, verdict: string) => {
    setBusyId(id);
    try {
      const r = await fetch(`${API}/api/v1/ml/anomaly-review/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
        body: JSON.stringify({ verdict }),
      });
      if (!r.ok) throw new Error('Failed to update anomaly review status');
      toast.success('Anomalie évaluée, merci.');
      setQ((prev) => prev ? { pending_count: prev.pending_count - 1, items: prev.items.filter((i) => i.id !== id) } : prev);
    } catch {
      toast.error("Échec de l'évaluation.");
    } finally {
      setBusyId(null);
    }
  };

  if (!q) return <div className="h-24 rounded-lg bg-slate-800 animate-pulse" />;

  if (q.items.length === 0) {
    return (
      <div className="flex gap-2 items-center rounded-lg bg-slate-800/60 border border-slate-700 px-4 py-3 text-sm text-slate-400">
        <CheckCircle className="h-4 w-4 text-emerald-400" /> Aucune anomalie en attente d'évaluation.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2 items-center rounded-lg bg-amber-950/40 border border-amber-800 px-4 py-2 text-sm text-amber-200">
        <AlertTriangle className="h-4 w-4" /> {q.pending_count} anomalie(s) détectée(s) en attente de confirmation technicien.
      </div>
      <div className="rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800 text-blue-300 text-xs">
            <tr>
              <th className="text-left px-3 py-2">Machine</th>
              <th className="text-left px-3 py-2">Score</th>
              <th className="text-left px-3 py-2">Détectée</th>
              <th className="text-left px-3 py-2">Vérification</th>
            </tr>
          </thead>
          <tbody>
            {q.items.map((f) => (
              <tr key={f.id} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-100">{f.machine_name ?? `#${f.machine_id}`}</td>
                <td className="px-3 py-2 text-slate-300">{f.anomaly_score?.toFixed(2) ?? '—'}</td>
                <td className="px-3 py-2 text-blue-300">{formatAgo(f.flagged_at)}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => submit(f.id, 'CONFIRMED')}
                      disabled={busyId === f.id}
                      title="Anomalie réelle confirmée"
                      className="inline-flex items-center gap-1 text-xs font-medium text-emerald-200 bg-emerald-900/40 border border-emerald-800 rounded-md px-2 py-1.5 hover:bg-emerald-900/70 disabled:opacity-50"
                    >
                      <CheckCircle className="h-3.5 w-3.5" /> Réelle
                    </button>
                    <button
                      onClick={() => submit(f.id, 'FALSE_POSITIVE')}
                      disabled={busyId === f.id}
                      title="Fausse alerte"
                      className="inline-flex items-center gap-1 text-xs font-medium text-red-200 bg-red-950/40 border border-red-800 rounded-md px-2 py-1.5 hover:bg-red-950/70 disabled:opacity-50"
                    >
                      <XCircle className="h-3.5 w-3.5" /> Fausse alerte
                    </button>
                    <button
                      onClick={() => submit(f.id, 'BENIGN_TRANSIENT')}
                      disabled={busyId === f.id}
                      title="Variation normale (démarrage, etc.)"
                      className="inline-flex items-center gap-1 text-xs font-medium text-slate-300 bg-slate-800 border border-slate-700 rounded-md px-2 py-1.5 hover:bg-slate-700/60 disabled:opacity-50"
                    >
                      <HelpCircle className="h-3.5 w-3.5" /> Normal
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
