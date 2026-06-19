import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { WhyDrawer } from './WhyDrawer';
import type { WhyPayload } from './whyTypes';

export function WhyButton({ payload, className = '' }: { payload: WhyPayload; className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}
        className={`inline-flex items-center gap-1 text-[11px] text-blue-300 hover:text-blue-200 ${className}`}>
        <HelpCircle className="h-3.5 w-3.5" /> Pourquoi ?
      </button>
      <WhyDrawer open={open} onOpenChange={setOpen} payload={payload} />
    </>
  );
}
