import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { client } from '@/lib/api';
import { WhyButton } from '@/modules/shared/explain/WhyButton';
import { buildBriefingWhy, BriefingFacts } from '@/modules/shared/explain/producers/buildBriefingWhy';

export function BriefingBar({ site = 'all' }: Readonly<{ site?: string }>) {
  const [text, setText] = useState<string | null>(null);
  const [facts, setFacts] = useState<BriefingFacts | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res: any = await (client.apiCall as any).invoke({
          url: `/api/v1/dashboard/briefing?site=${encodeURIComponent(site)}`,
          method: 'GET',
        });
        const data = res?.data ?? res;
        if (alive) { setText(data?.text ?? null); setFacts(data?.facts ?? null); }
      } catch {
        if (alive) setText(null); // bar simply hides on failure
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [site]);

  if (loading) return <div className="h-16 rounded-lg bg-slate-800 animate-pulse mb-4" />;
  if (!text) return null;

  return (
    <div className="flex gap-3 items-start rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 mb-4">
      <Sparkles className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm text-blue-100 leading-relaxed">
          <span className="font-medium text-white">Briefing du jour. </span>{text}
        </p>
        {facts && <div className="mt-2"><WhyButton payload={buildBriefingWhy(facts)} /></div>}
      </div>
    </div>
  );
}
