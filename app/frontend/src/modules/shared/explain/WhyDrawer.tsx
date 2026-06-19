import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import type { WhyPayload, WhyTone } from './whyTypes';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

const TONE: Record<WhyTone, string> = {
  critical: 'border-l-red-500', warning: 'border-l-amber-500',
  normal: 'border-l-blue-500', info: 'border-l-slate-500',
};

export function WhyDrawer({ open, onOpenChange, payload }:
  { open: boolean; onOpenChange: (o: boolean) => void; payload: WhyPayload | null }) {
  const [plain, setPlain] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!payload) return null;

  const explain = async () => {
    setBusy(true);
    try {
      const reasons = (payload.llmContext?.reasons as string[]) ?? payload.reasons.map((r) => r.label);
      const res = await fetch(`${API}/api/v1/why/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ reasons }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail ?? 'failed');
      setPlain(data?.text ?? null);
    } catch {
      toast.error('Explication indisponible pour le moment.');
    } finally { setBusy(false); }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="bg-slate-900 border-slate-700 text-slate-100 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-white">{payload.title}</SheetTitle>
          <SheetDescription className="text-blue-300">{payload.summary}</SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-2">
          {payload.reasons.map((r, i) => (
            <div key={i} className={`bg-slate-800 border border-slate-700 border-l-[3px] ${TONE[r.tone ?? 'info']} rounded-md px-3 py-2`}>
              <p className="text-sm text-slate-100">{r.label}</p>
              {r.detail && <p className="text-xs text-blue-300">{r.detail}</p>}
            </div>
          ))}
        </div>

        {payload.confidence && (
          <div className="mt-4 text-sm text-slate-200">
            Confiance : <span className="font-medium">{payload.confidence.level}</span>
            <span className="text-blue-300"> — {payload.confidence.note}</span>
          </div>
        )}

        {payload.counterfactual && (
          <div className="mt-4">
            <p className="text-xs font-medium text-emerald-400 mb-2">Pour revenir à la normale</p>
            <div className="space-y-2">
              {payload.counterfactual.map((r, i) => (
                <div key={i} className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100">{r.label}</div>
              ))}
            </div>
          </div>
        )}

        <button onClick={explain} disabled={busy}
          className="mt-5 inline-flex items-center gap-2 text-xs font-medium text-blue-300 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 hover:bg-slate-700/60 disabled:opacity-50">
          <Sparkles className="h-4 w-4" /> {busy ? 'Explication…' : 'Expliquer simplement'}
        </button>
        {plain && <p className="mt-3 text-sm text-blue-100 leading-relaxed">{plain}</p>}

        <p className="mt-5 pt-3 border-t border-slate-800 text-[11px] text-slate-500">{payload.source}</p>
      </SheetContent>
    </Sheet>
  );
}
