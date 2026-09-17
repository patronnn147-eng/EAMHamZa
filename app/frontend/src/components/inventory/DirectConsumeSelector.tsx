/**
 * DirectConsumeSelector — pick pieces from inventory at WO completion time.
 *
 * Used by WO completion dialogs when there are NO prior reservations
 * (technician picks from the catalog ad-hoc). Mirrors the PiecePicker UX
 * but produces a flat `parts_consumed_direct` payload (piece_id + qty).
 *
 * Supports inline pending submission for parts not in the catalog.
 *
 * Live availability checking + max enforcement identical to PiecePicker.
 */
import { useCallback, useMemo, useRef, useState } from 'react';
import { Plus, Minus, Search, FileQuestion, Box, Beaker, Library } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useMachinePieces, PickerPiece } from '@/hooks/useInventory';
import { SectionDivider, BlueprintBackground } from './primitives';

export interface DirectConsumeRow {
  piece_id: number;
  piece_name: string;
  piece_reference: string;
  quantity: string;
  unit: string;
  available_quantity: number;
  stock_quantity: number;
  min_stock: number | null;
  notes: string;
}

export interface PendingDraftRow {
  name: string;
  quantity: string;
  unit: string;
  category: string;
  notes: string;
}

interface DirectConsumeSelectorProps {
  machineId: number | null;
  consumedRows: DirectConsumeRow[];
  pendingRows: PendingDraftRow[];
  onConsumedChange: (rows: DirectConsumeRow[]) => void;
  onPendingChange: (rows: PendingDraftRow[]) => void;
}

/** Helper for parent to know if any row has invalid qty (block submit). */
export function directHasErrors(rows: DirectConsumeRow[]): boolean {
  return rows.some((r) => {
    const q = Number(r.quantity);
    return !Number.isFinite(q) || q <= 0 || q > r.available_quantity;
  });
}

/** Serialize for API. */
export function serializeDirect(rows: DirectConsumeRow[]) {
  return rows.map((r) => ({
    piece_id: r.piece_id,
    quantity: Number(r.quantity),
    unit: r.unit,
    notes: r.notes || undefined,
  }));
}

/** Serialize pending drafts for API. */
export function serializePendingDirect(rows: PendingDraftRow[]) {
  return rows
    .filter((r) => r.name && r.name.trim())
    .map((r) => ({
      name: r.name.trim(),
      quantity: Number(r.quantity || 1),
      unit: r.unit || 'pcs',
      category: r.category || undefined,
      notes: r.notes || undefined,
    }));
}

export function DirectConsumeSelector({
  machineId,
  consumedRows,
  pendingRows,
  onConsumedChange,
  onPendingChange,
}: Readonly<DirectConsumeSelectorProps>) {
  const [search, setSearch] = useState('');
  const { data, loading } = useMachinePieces(machineId, search.length >= 2 ? search : undefined);

  // Stable per-row React keys for pendingRows, independent of the plain-data
  // shape sent to the API (pendingRows itself carries no id field).
  const pendingRowKeysRef = useRef<string[]>([]);

  const selectedIds = useMemo(() => new Set(consumedRows.map((r) => r.piece_id)), [consumedRows]);

  const addPiece = useCallback(
    (piece: PickerPiece) => {
      if (selectedIds.has(piece.id)) return;
      const avail = Number(piece.available_quantity ?? piece.stock_quantity ?? 0);
      if (avail <= 0) return;
      onConsumedChange([
        ...consumedRows,
        {
          piece_id: piece.id,
          piece_name: piece.name,
          piece_reference: piece.reference,
          quantity: '1',
          unit: piece.default_unit || 'pcs',
          available_quantity: avail,
          stock_quantity: Number(piece.stock_quantity ?? 0),
          min_stock: piece.min_stock,
          notes: '',
        },
      ]);
    },
    [consumedRows, selectedIds, onConsumedChange],
  );

  const removePiece = useCallback(
    (piece_id: number) => onConsumedChange(consumedRows.filter((r) => r.piece_id !== piece_id)),
    [consumedRows, onConsumedChange],
  );

  const updateRow = useCallback(
    (piece_id: number, patch: Partial<DirectConsumeRow>) =>
      onConsumedChange(consumedRows.map((r) => (r.piece_id === piece_id ? { ...r, ...patch } : r))),
    [consumedRows, onConsumedChange],
  );

  const addPendingDraft = useCallback(() => {
    pendingRowKeysRef.current.push(crypto.randomUUID());
    onPendingChange([...pendingRows, { name: '', quantity: '1', unit: 'pcs', category: '', notes: '' }]);
  }, [pendingRows, onPendingChange]);

  const updateDraft = useCallback(
    (idx: number, patch: Partial<PendingDraftRow>) =>
      onPendingChange(pendingRows.map((d, i) => (i === idx ? { ...d, ...patch } : d))),
    [pendingRows, onPendingChange],
  );

  const removeDraft = useCallback(
    (idx: number) => {
      pendingRowKeysRef.current.splice(idx, 1);
      onPendingChange(pendingRows.filter((_, i) => i !== idx));
    },
    [pendingRows, onPendingChange],
  );

  const compatible = data?.compatible ?? [];
  const consumables = data?.consumables ?? [];
  const other = data?.other ?? [];
  const anyExceeds = consumedRows.some((r) => Number(r.quantity) > r.available_quantity);

  return (
    <div className="relative space-y-4">
      <BlueprintBackground className="rounded-md" />

      {/* Consumed rows — current selections */}
      {consumedRows.length > 0 && (
        <div className="relative space-y-2 rounded-md border border-emerald-500/30 bg-emerald-950/20 p-3">
          <SectionDivider
            label={`Pièces consommées · ${consumedRows.length}`}
            tone={anyExceeds ? 'danger' : 'success'}
          />
          <div className="space-y-1.5">
            {consumedRows.map((row) => {
              const q = Number(row.quantity);
              const exceeds = q > row.available_quantity;
              return (
                <div
                  key={row.piece_id}
                  className={`flex items-center gap-2 rounded px-2 py-1.5 ${
                    exceeds
                      ? 'bg-red-950/30 border border-red-500/40'
                      : 'bg-slate-900/60 border border-emerald-500/20'
                  }`}
                >
                  <span className="font-mono text-[10px] text-blue-400 tracking-wider min-w-[80px]">
                    {row.piece_reference}
                  </span>
                  <span className="flex-1 text-sm text-white truncate">{row.piece_name}</span>
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    max={row.available_quantity}
                    value={row.quantity}
                    onChange={(e) => updateRow(row.piece_id, { quantity: e.target.value })}
                    className={`w-20 h-7 font-mono tabular-nums text-right bg-slate-950/60 focus-visible:ring-emerald-400/50 ${
                      exceeds ? 'text-red-300 border-red-500/60' : 'text-emerald-300 border-emerald-500/30'
                    }`}
                    aria-invalid={exceeds}
                  />
                  <span className="font-mono text-[10px] text-blue-400 min-w-[28px]">{row.unit}</span>
                  <span className="font-mono text-[10px] tabular-nums text-blue-400/70 whitespace-nowrap">
                    dispo{' '}
                    <span className={row.available_quantity <= 0 ? 'text-red-400 font-bold' : 'text-emerald-300 font-semibold'}>
                      {row.available_quantity}
                    </span>
                    {row.unit}
                  </span>
                  <button
                    type="button"
                    onClick={() => removePiece(row.piece_id)}
                    className="ml-1 text-red-400/70 hover:text-red-300 transition-colors"
                    title="Retirer"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
            {anyExceeds && (
              <p className="text-[11px] text-red-400 font-mono mt-1 px-1 flex items-center gap-1">
                <span className="text-red-500">▲</span>
                Une ou plusieurs quantités dépassent le stock disponible.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Pending uncatalogued */}
      {pendingRows.length > 0 && (
        <div className="relative space-y-2 rounded-md border border-amber-500/30 bg-amber-950/20 p-3">
          <SectionDivider label={`Demandes de pièces non-cataloguées · ${pendingRows.length}`} tone="warning" />
          <div className="space-y-1.5">
            {pendingRows.map((d, i) => {
              if (!pendingRowKeysRef.current[i]) pendingRowKeysRef.current[i] = crypto.randomUUID();
              return (
              <div
                key={pendingRowKeysRef.current[i]}
                className="grid grid-cols-12 gap-1.5 items-center rounded bg-slate-900/60 border border-amber-500/20 px-2 py-1.5"
              >
                <Input
                  placeholder="Nom de la pièce"
                  value={d.name}
                  onChange={(e) => updateDraft(i, { name: e.target.value })}
                  className="col-span-5 h-7 text-sm bg-slate-950/60 border-amber-500/30 placeholder:text-amber-300/40"
                />
                <Input
                  placeholder="Cat."
                  value={d.category}
                  onChange={(e) => updateDraft(i, { category: e.target.value })}
                  className="col-span-2 h-7 text-xs bg-slate-950/60 border-amber-500/20"
                />
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={d.quantity}
                  onChange={(e) => updateDraft(i, { quantity: e.target.value })}
                  className="col-span-2 h-7 font-mono tabular-nums text-right text-amber-300 bg-slate-950/60 border-amber-500/30"
                />
                <Input
                  placeholder="unit"
                  value={d.unit}
                  onChange={(e) => updateDraft(i, { unit: e.target.value })}
                  className="col-span-2 h-7 font-mono text-xs text-center text-amber-200/80 bg-slate-950/60 border-amber-500/20"
                />
                <button
                  type="button"
                  onClick={() => removeDraft(i)}
                  className="col-span-1 text-red-400/70 hover:text-red-300 transition-colors flex justify-center"
                  title="Retirer"
                >
                  <Minus className="h-4 w-4" />
                </button>
              </div>
              );
            })}
          </div>
          <p className="text-[10px] text-amber-400/70 font-mono tracking-wider px-1">
            ⚠ ces demandes seront envoyées à l'admin pour validation après l'OT
          </p>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-blue-400/60" />
        <Input
          placeholder="Rechercher dans tout le catalogue…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-9 bg-slate-950/60 border-blue-500/30 placeholder:text-blue-400/40 font-mono text-sm"
        />
      </div>

      {/* Sections */}
      {Boolean(machineId) && (
        <PickerSection
          icon={<Box className="h-3 w-3" />}
          label="Pièces compatibles machine"
          count={compatible.length}
          loading={loading}
        >
          {compatible.map((p) => (
            <PieceRow key={p.id} piece={p} selected={selectedIds.has(p.id)} onAdd={() => addPiece(p)} />
          ))}
        </PickerSection>
      )}

      {consumables.length > 0 && (
        <PickerSection
          icon={<Beaker className="h-3 w-3" />}
          label="Consommables"
          count={consumables.length}
          loading={false}
        >
          {consumables.map((p) => (
            <PieceRow key={p.id} piece={p} selected={selectedIds.has(p.id)} onAdd={() => addPiece(p)} />
          ))}
        </PickerSection>
      )}

      {search.length >= 2 && other.length > 0 && (
        <PickerSection
          icon={<Library className="h-3 w-3" />}
          label={`Catalogue complet · "${search}"`}
          count={other.length}
          loading={loading}
        >
          {other.map((p) => (
            <PieceRow key={p.id} piece={p} selected={selectedIds.has(p.id)} onAdd={() => addPiece(p)} />
          ))}
        </PickerSection>
      )}

      {/* Pending request inline */}
      <div className="relative rounded-md border border-dashed border-amber-500/30 bg-amber-950/10 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-amber-400/80">
            <FileQuestion className="h-4 w-4" />
            <div>
              <p className="text-xs font-mono uppercase tracking-wider">Pièce indisponible ou non-cataloguée ?</p>
              <p className="text-[10px] text-amber-400/50 mt-0.5">
                Saisir manuellement · l'admin la validera après l'OT
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={addPendingDraft}
            className="h-7 border-amber-500/40 text-amber-300 hover:bg-amber-500/10 font-mono text-[11px] tracking-wider"
          >
            <Plus className="h-3 w-3 mr-1" />
            DEMANDER
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Subcomponents ──────────────────────────────────────────────────

interface PickerSectionProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  loading: boolean;
  children: React.ReactNode;
}

function PickerSection({ icon, label, count, loading, children }: Readonly<PickerSectionProps>) {
  return (
    <div className="relative rounded-md border border-blue-500/20 bg-slate-950/40 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-blue-500/10 bg-slate-900/60">
        <span className="text-blue-400/80">{icon}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-blue-300/80">{label}</span>
        <span className="font-mono text-[10px] text-blue-400/50 tabular-nums">[{count}]</span>
        {loading && <span className="ml-auto text-blue-400/50 text-[10px] font-mono animate-pulse">…</span>}
      </div>
      <div className="max-h-48 overflow-y-auto divide-y divide-blue-500/5">
        {(!children || (Array.isArray(children) && children.length === 0)) && (
          <div className="px-3 py-2 text-[11px] text-blue-400/40 font-mono">(aucune pièce)</div>
        )}
        {children}
      </div>
    </div>
  );
}

interface PieceRowProps {
  piece: PickerPiece;
  selected: boolean;
  onAdd: () => void;
}

function PieceRow({ piece, selected, onAdd }: Readonly<PieceRowProps>) {
  const stockQty = Number(piece.stock_quantity ?? 0);
  const avail = Number(piece.available_quantity ?? stockQty);
  const reserved = Number(piece.reserved_quantity ?? 0);
  const rupture = avail <= 0;
  const lowAvail = !rupture && piece.min_stock != null && avail < Number(piece.min_stock);
  const disabled = selected || rupture;

  let rowStateClass: string;
  let refStateClass: string;
  let nameStateClass: string;
  if (selected) {
    rowStateClass = 'bg-emerald-500/5 cursor-default';
    refStateClass = 'text-emerald-400/60';
    nameStateClass = 'text-emerald-300/80';
  } else if (rupture) {
    rowStateClass = 'bg-red-950/20 cursor-not-allowed opacity-60';
    refStateClass = 'text-red-400/80';
    nameStateClass = 'text-red-300/70 line-through';
  } else {
    rowStateClass = 'hover:bg-blue-500/5 cursor-pointer';
    refStateClass = 'text-blue-400/80';
    nameStateClass = 'text-blue-100';
  }

  let trailingIndicator: React.ReactNode;
  if (selected) {
    trailingIndicator = (
      <span className="text-emerald-400/60 font-mono text-[10px] uppercase tracking-wider">sélectionnée</span>
    );
  } else if (rupture) {
    trailingIndicator = (
      <span className="text-red-400/60 font-mono text-[10px] uppercase tracking-wider">indispo</span>
    );
  } else {
    trailingIndicator = <Plus className="h-3.5 w-3.5 text-blue-400/60" />;
  }

  return (
    <button
      type="button"
      onClick={onAdd}
      disabled={disabled}
      className={`w-full flex items-center gap-3 px-3 py-1.5 text-left transition-colors ${rowStateClass}`}
      title={rupture ? `Rupture · 0 ${piece.default_unit} disponibles` : undefined}
    >
      <span
        className={`font-mono text-[10px] tracking-wider min-w-[80px] ${refStateClass}`}
      >
        {piece.reference}
      </span>
      <span
        className={`flex-1 text-sm truncate ${nameStateClass}`}
      >
        {piece.name}
      </span>
      <span className="font-mono text-[10px] tabular-nums whitespace-nowrap">
        {rupture ? (
          <span className="text-red-400 font-bold uppercase tracking-wider">RUPTURE</span>
        ) : (
          <>
            <span className={`font-semibold ${lowAvail ? 'text-amber-400' : 'text-emerald-300'}`}>{avail}</span>
            <span className="text-blue-400/60 ml-0.5">{piece.default_unit}</span>
            {reserved > 0 && <span className="text-blue-400/40 ml-1">/{stockQty} (résv.{reserved})</span>}
            {lowAvail && <span className="text-amber-400 ml-1">▼</span>}
          </>
        )}
      </span>
      {trailingIndicator}
    </button>
  );
}
