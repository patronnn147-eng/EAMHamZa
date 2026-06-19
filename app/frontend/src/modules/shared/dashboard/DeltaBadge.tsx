import { computeDelta } from './computeDelta';

export function DeltaBadge({ current, previous }: { current: number; previous?: number }) {
  const d = computeDelta(current, previous);
  const color =
    d.direction === 'up' ? 'text-emerald-400'
    : d.direction === 'down' ? 'text-red-400'
    : 'text-blue-300';
  return <span className={`text-[11px] ${color}`}>{d.label} vs hier</span>;
}
