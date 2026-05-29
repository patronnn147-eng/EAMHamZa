/**
 * Shared visual primitives for the inventory workflow.
 *
 * Aesthetic: "workshop precision". Mono numerals, phosphor-green for
 * confidence, warm amber for medium signal, red-orange for rupture.
 * ASCII section dividers + custom tier glyphs = technical character.
 */
import React from 'react';

// ─── Section divider (ASCII brackets, e.g. ──┤ LABEL ├──) ────────────────

interface SectionDividerProps {
  label: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
  className?: string;
}

export function SectionDivider({ label, tone = 'default', className = '' }: SectionDividerProps) {
  const toneClass = {
    default: 'text-blue-400/60',
    success: 'text-emerald-400/80',
    warning: 'text-amber-400/80',
    danger:  'text-red-400/80',
  }[tone];

  return (
    <div className={`flex items-center gap-2 select-none font-mono text-[10px] uppercase tracking-[0.18em] ${toneClass} ${className}`}>
      <span aria-hidden="true" className="flex-1 border-t border-current opacity-40" />
      <span className="px-1">┤ {label} ├</span>
      <span aria-hidden="true" className="flex-1 border-t border-current opacity-40" />
    </div>
  );
}

// ─── Tier glyph: stacked chevrons (high=3, medium=2, low=1) ──────────────

interface TierBadgeProps {
  tier: 'high' | 'medium' | 'low';
  similarity?: number;
  machineMatch?: boolean;
}

export function TierBadge({ tier, similarity, machineMatch }: TierBadgeProps) {
  const config = {
    high:   { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-400/40', count: 3, label: 'MATCH' },
    medium: { color: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-400/40',   count: 2, label: 'POSSIBLE' },
    low:    { color: 'text-slate-400',   bg: 'bg-slate-500/10',   border: 'border-slate-400/30',   count: 1, label: 'FAIBLE' },
  }[tier];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider tabular-nums ${config.color} ${config.bg} ${config.border}`}
    >
      <span className="flex flex-col leading-none -space-y-[3px]" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, i) => (
          <span
            key={i}
            className={i < config.count ? 'opacity-100' : 'opacity-20'}
            style={{ fontSize: '8px' }}
          >▲</span>
        ))}
      </span>
      <span className="leading-none">
        {config.label}
        {similarity !== undefined && (
          <span className="ml-1 opacity-70">{(similarity * 100).toFixed(0)}%</span>
        )}
      </span>
      {machineMatch && (
        <span title="Machine compatible" className="leading-none">⚙</span>
      )}
    </span>
  );
}

// ─── Numeric badge: mono, tabular, color-coded vs stock state ────────────

interface QtyBadgeProps {
  value: string | number;
  min?: number | string | null;
  unit?: string;
  reserved?: string | number;
  className?: string;
}

export function QtyBadge({ value, min, unit = 'pcs', reserved, className = '' }: QtyBadgeProps) {
  const v = Number(value);
  const m = min != null ? Number(min) : null;
  const r = reserved != null ? Number(reserved) : 0;
  const available = v - r;

  let tone: 'ok' | 'low' | 'rupture';
  if (available <= 0) tone = 'rupture';
  else if (m != null && available < m) tone = 'low';
  else tone = 'ok';

  const colorClass = {
    ok:      'text-emerald-400',
    low:     'text-amber-400',
    rupture: 'text-red-400',
  }[tone];

  return (
    <span className={`font-mono tabular-nums ${colorClass} ${className}`}>
      <span className="font-semibold">{formatNum(available)}</span>
      <span className="ml-0.5 text-[0.85em] opacity-60">{unit}</span>
      {r > 0 && (
        <span className="ml-1 text-[0.7em] opacity-50">
          /{formatNum(v)} (résv. {formatNum(r)})
        </span>
      )}
      {m != null && (
        <span className="ml-1 text-[0.7em] opacity-40">
          min {formatNum(m)}
        </span>
      )}
    </span>
  );
}

// ─── Blueprint grid background (composable overlay) ──────────────────────

export function BlueprintBackground({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 opacity-[0.07] ${className}`}
      style={{
        backgroundImage:
          "linear-gradient(rgba(125,211,252,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(125,211,252,0.5) 1px, transparent 1px)",
        backgroundSize: '24px 24px',
      }}
    />
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────

export function formatNum(value: number | string | null | undefined): string {
  if (value == null) return '—';
  const n = typeof value === 'string' ? Number(value) : value;
  if (Number.isNaN(n)) return '—';
  // Show up to 2 decimal places, trim trailing zeros
  return Number(n.toFixed(2)).toString();
}

export function relTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `il y a ${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `il y a ${min}min`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `il y a ${hr}h`;
  const day = Math.floor(hr / 24);
  return `il y a ${day}j`;
}
