/**
 * PartsConsumedSelector — completion-time consumption editor.
 *
 * Pre-filled from `required_pieces` (reservations). For each row the
 * technician picks a disposition; "partial" expands into used/returned/wasted
 * fields with live sum validation against the reservation.
 */
import React, { useCallback, useMemo } from 'react';
import { CheckCircle2, ArrowDownToLine, ArrowUpFromLine, XCircle, RotateCcw, AlertTriangle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { RequiredPiece } from '@/hooks/useInventory';
import { SectionDivider, BlueprintBackground, formatNum } from './primitives';

type Disposition = 'used' | 'partial' | 'not_used' | 'wasted' | 'returned';

export interface ConsumedRow {
  required_piece_id: number;
  piece_id: number;
  piece_name: string;
  piece_reference: string;
  unit: string;
  planned: number;
  quantity_used: string;
  quantity_returned: string;
  quantity_wasted: string;
  disposition: Disposition;
  notes: string;
}

interface PartsConsumedSelectorProps {
  required: RequiredPiece[];
  rows: ConsumedRow[];
  onChange: (rows: ConsumedRow[]) => void;
}

const DISPOSITION_META: Record<Disposition, { label: string; icon: React.ComponentType<{ className?: string }>; tone: string }> = {
  used:     { label: 'Utilisée intégralement',  icon: CheckCircle2,    tone: 'emerald' },
  partial:  { label: 'Utilisation partielle',   icon: ArrowDownToLine, tone: 'amber' },
  not_used: { label: 'Non utilisée',            icon: XCircle,         tone: 'slate' },
  wasted:   { label: 'Perdue / cassée',         icon: AlertTriangle,   tone: 'red' },
  returned: { label: 'Retournée au stock',      icon: RotateCcw,       tone: 'blue' },
};

/** Derive consumed rows from required-pieces fetched from API. */
export function buildInitialConsumedRows(required: RequiredPiece[]): ConsumedRow[] {
  return required.map((rp) => ({
    required_piece_id: rp.id,
    piece_id: rp.piece_id,
    piece_name: rp.piece_name,
    piece_reference: rp.piece_reference,
    unit: rp.unit,
    planned: Number(rp.quantity_planned),
    quantity_used: rp.quantity_planned,
    quantity_returned: '0',
    quantity_wasted: '0',
    disposition: 'used',
    notes: '',
  }));
}

export function PartsConsumedSelector({ required, rows, onChange }: PartsConsumedSelectorProps) {
  const setRow = useCallback((idx: number, patch: Partial<ConsumedRow>) => {
    onChange(rows.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  }, [rows, onChange]);

  if (required.length === 0) {
    return (
      <div className="relative rounded-md border border-blue-500/30 bg-slate-950/40 px-4 py-6 text-center">
        <BlueprintBackground />
        <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-blue-400/60">
          Aucune pièce n'était prévue · saisie libre uniquement
        </p>
      </div>
    );
  }

  return (
    <div className="relative space-y-3">
      <BlueprintBackground className="rounded-md" />
      <SectionDivider label={`Consommation réelle · ${rows.length}`} tone="success" />

      <div className="space-y-2">
        {rows.map((row, i) => (
          <ConsumedRowCard
            key={row.required_piece_id}
            row={row}
            onChange={(patch) => setRow(i, patch)}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Single-row card ────────────────────────────────────────────────────

interface RowCardProps {
  row: ConsumedRow;
  onChange: (patch: Partial<ConsumedRow>) => void;
}

function ConsumedRowCard({ row, onChange }: RowCardProps) {
  const used = Number(row.quantity_used || 0);
  const returned = Number(row.quantity_returned || 0);
  const wasted = Number(row.quantity_wasted || 0);
  const total = used + returned + wasted;
  const overflow = total > row.planned;
  const remaining = row.planned - total;

  const setDisposition = (d: Disposition) => {
    let patch: Partial<ConsumedRow> = { disposition: d };
    switch (d) {
      case 'used':
        patch = { ...patch, quantity_used: String(row.planned), quantity_returned: '0', quantity_wasted: '0' };
        break;
      case 'not_used':
        patch = { ...patch, quantity_used: '0', quantity_returned: '0', quantity_wasted: '0' };
        break;
      case 'wasted':
        patch = { ...patch, quantity_used: '0', quantity_returned: '0', quantity_wasted: String(row.planned) };
        break;
      case 'returned':
        patch = { ...patch, quantity_used: '0', quantity_returned: String(row.planned), quantity_wasted: '0' };
        break;
      case 'partial':
        // keep current values; user fills the split
        break;
    }
    onChange(patch);
  };

  return (
    <div className={`relative rounded-md border bg-slate-950/60 overflow-hidden ${overflow ? 'border-red-500/40' : 'border-blue-500/20'}`}>
      {/* Header row — piece + planned + disposition pills */}
      <div className="flex items-center gap-3 px-3 py-2 border-b border-blue-500/10 bg-slate-900/40">
        <span className="font-mono text-[10px] tracking-wider text-blue-400/80 min-w-[80px]">{row.piece_reference}</span>
        <span className="flex-1 text-sm text-white truncate">{row.piece_name}</span>
        <span className="font-mono text-[11px] tabular-nums text-blue-300">
          <span className="opacity-60">prévue</span>
          <span className="ml-1.5 font-semibold text-blue-100">{formatNum(row.planned)}</span>
          <span className="ml-0.5 opacity-60">{row.unit}</span>
        </span>
      </div>

      {/* Disposition pill row */}
      <div className="flex flex-wrap gap-1.5 px-3 py-2 border-b border-blue-500/10">
        {(Object.keys(DISPOSITION_META) as Disposition[]).map((d) => {
          const meta = DISPOSITION_META[d];
          const Icon = meta.icon;
          const active = row.disposition === d;
          const toneCls = {
            emerald: active ? 'border-emerald-400 bg-emerald-500/15 text-emerald-300' : 'border-slate-700 text-slate-400 hover:border-emerald-500/50',
            amber:   active ? 'border-amber-400 bg-amber-500/15 text-amber-300'       : 'border-slate-700 text-slate-400 hover:border-amber-500/50',
            slate:   active ? 'border-slate-400 bg-slate-500/15 text-slate-200'       : 'border-slate-700 text-slate-400 hover:border-slate-500',
            red:     active ? 'border-red-400 bg-red-500/15 text-red-300'             : 'border-slate-700 text-slate-400 hover:border-red-500/50',
            blue:    active ? 'border-blue-400 bg-blue-500/15 text-blue-300'          : 'border-slate-700 text-slate-400 hover:border-blue-500/50',
          }[meta.tone] || '';
          return (
            <button
              key={d}
              type="button"
              onClick={() => setDisposition(d)}
              className={`flex items-center gap-1.5 rounded border px-2 py-1 text-[10px] font-mono uppercase tracking-wider transition-all ${toneCls}`}
            >
              <Icon className="h-3 w-3" />
              {meta.label}
            </button>
          );
        })}
      </div>

      {/* Quantity split (only relevant for 'partial' or when overflow) */}
      {row.disposition === 'partial' && (
        <div className="grid grid-cols-3 gap-2 px-3 py-2 border-b border-blue-500/10 bg-slate-900/20">
          <QtyField
            label="USED"
            color="emerald"
            value={row.quantity_used}
            unit={row.unit}
            onChange={(v) => onChange({ quantity_used: v })}
          />
          <QtyField
            label="RETOUR"
            color="blue"
            value={row.quantity_returned}
            unit={row.unit}
            onChange={(v) => onChange({ quantity_returned: v })}
          />
          <QtyField
            label="REBUT"
            color="red"
            value={row.quantity_wasted}
            unit={row.unit}
            onChange={(v) => onChange({ quantity_wasted: v })}
          />
        </div>
      )}

      {/* Sum bar */}
      <div className="flex items-center justify-between gap-3 px-3 py-1.5 text-[10px] font-mono tabular-nums">
        <div className="flex gap-3 text-blue-400/70">
          <span>used <span className="text-emerald-400">{formatNum(used)}</span></span>
          <span>retour <span className="text-blue-300">{formatNum(returned)}</span></span>
          <span>rebut <span className="text-red-400">{formatNum(wasted)}</span></span>
        </div>
        <div>
          {overflow ? (
            <span className="text-red-400 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              dépasse plan de {formatNum(total - row.planned)}{row.unit}
            </span>
          ) : remaining > 0 ? (
            <span className="text-blue-400/60">
              reste {formatNum(remaining)}{row.unit} sur réservation
            </span>
          ) : (
            <span className="text-emerald-400/80">total = plan ✓</span>
          )}
        </div>
      </div>

      {/* Optional notes — only when needed */}
      {(row.disposition === 'wasted' || row.disposition === 'partial') && (
        <div className="px-3 pb-2">
          <Textarea
            placeholder={row.disposition === 'wasted' ? 'Cause du rebut (obligatoire pour rapport)…' : 'Notes (optionnel)…'}
            value={row.notes}
            onChange={(e) => onChange({ notes: e.target.value })}
            className="min-h-[40px] text-xs bg-slate-950/40 border-blue-500/20"
            rows={2}
          />
        </div>
      )}
    </div>
  );
}

interface QtyFieldProps {
  label: string;
  color: 'emerald' | 'blue' | 'red';
  value: string;
  unit: string;
  onChange: (v: string) => void;
}

function QtyField({ label, color, value, unit, onChange }: QtyFieldProps) {
  const colorMap = {
    emerald: 'border-emerald-500/30 text-emerald-300 focus-visible:ring-emerald-400/50',
    blue:    'border-blue-500/30 text-blue-300 focus-visible:ring-blue-400/50',
    red:     'border-red-500/30 text-red-300 focus-visible:ring-red-400/50',
  }[color];
  return (
    <label className="flex flex-col gap-1">
      <span className={`font-mono text-[9px] uppercase tracking-[0.18em] ${color === 'emerald' ? 'text-emerald-400' : color === 'blue' ? 'text-blue-400' : 'text-red-400'}`}>
        {label} <span className="opacity-60">[{unit}]</span>
      </span>
      <Input
        type="number"
        min="0"
        step="0.01"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`h-7 font-mono tabular-nums text-right bg-slate-950/60 ${colorMap}`}
      />
    </label>
  );
}

/** Serialize consumed rows for API. */
export function serializeConsumedRows(rows: ConsumedRow[]) {
  return rows.map((r) => ({
    required_piece_id: r.required_piece_id,
    quantity_used: Number(r.quantity_used || 0),
    quantity_returned: Number(r.quantity_returned || 0),
    quantity_wasted: Number(r.quantity_wasted || 0),
    disposition: r.disposition,
    notes: r.notes || undefined,
  }));
}
