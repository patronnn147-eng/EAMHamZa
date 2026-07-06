import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface ModelRow { key: string; label: string; in_backend: boolean; in_micro: boolean; hash_match: boolean; mtime_backend: number | null }
interface Health { models: ModelRow[]; divergences: { filename: string; reason: string }[]; drift: { verdict: string }; retrain: { recommended: boolean; reasons: string[] } }

function ago(mtime: number | null): string {
  if (!mtime) return '—';
  const d = Math.floor((Date.now() / 1000 - mtime) / 86400);
  return d <= 0 ? "aujourd'hui" : `il y a ${d} j`;
}

export function ModelHealthTable() {
  const [h, setH] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = await fetch(`${API}/api/v1/ml/model-health`, { headers: { Authorization: `Bearer ${token()}` } });
      if (r.ok) setH(await r.json());
    } catch { /* leave null */ }
  };
  useEffect(() => { load(); }, []);

  const retrain = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/ml/retrain`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
        body: JSON.stringify({ model_type: 'all' }),
      });
      const j = await r.json();
      toast.success(j?.message ?? 'Réentraînement lancé.');
      load();
    } catch { toast.error('Réentraînement indisponible.'); }
    finally { setBusy(false); }
  };

  if (!h) return <div className="h-32 rounded-lg bg-slate-800 animate-pulse" />;

  return (
    <div className="space-y-3">
      {h.divergences.length > 0 && (
        <div className="flex gap-2 items-center rounded-lg bg-red-950 border border-red-800 px-4 py-2 text-sm text-red-200">
          <AlertTriangle className="h-4 w-4" /> {h.divergences.length} modèle(s) désynchronisé(s) entre les deux dossiers.
        </div>
      )}
      <div className="rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800 text-blue-300 text-xs">
            <tr><th className="text-left px-3 py-2">Modèle</th><th className="text-left px-3 py-2">Synchro</th><th className="text-left px-3 py-2">Dernier entraînement</th></tr>
          </thead>
          <tbody>
            {h.models.map((m) => {
              const inSync = m.in_backend && m.in_micro && m.hash_match;

              let mismatchReason = 'diffère';
              if (!m.in_micro) {
                mismatchReason = 'manquant côté service';
              } else if (!m.in_backend) {
                mismatchReason = 'manquant côté moteur';
              }

              return (
              <tr key={m.key} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-100">{m.label}</td>
                <td className="px-3 py-2">
                  {inSync
                    ? <span className="text-emerald-400 inline-flex items-center gap-1"><CheckCircle className="h-3.5 w-3.5" /> à jour</span>
                    : <span className="text-red-400 inline-flex items-center gap-1"><AlertTriangle className="h-3.5 w-3.5" /> {mismatchReason}</span>}
                </td>
                <td className="px-3 py-2 text-blue-300">{ago(m.mtime_backend)}</td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3">
        {h.retrain.recommended && <span className="text-xs text-amber-400">Réentraînement recommandé : {h.retrain.reasons.join(', ')}</span>}
        <button onClick={() => { if (confirm('Lancer le réentraînement des modèles ?')) retrain(); }} disabled={busy}
          className="ml-auto inline-flex items-center gap-2 text-xs font-medium text-blue-200 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 hover:bg-slate-700/60 disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} /> Réentraîner
        </button>
      </div>
    </div>
  );
}
