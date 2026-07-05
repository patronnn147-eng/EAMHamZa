/**
 * PiecePicker — multi-row planned-pieces selector for intervention requests.
 *
 * Aesthetic: workshop precision. Three sections (compatible / consumables /
 * search-all). Mono numerals + live availability badges. Pending-piece
 * submission inline at the bottom — no extra dialog.
 *
 * Availability enforcement:
 *   - `available_quantity = stock_quantity − Σ active reservations`
 *   - Catalog rows with `available_quantity <= 0` are disabled + show RUPTURE
 *   - Plan row qty input has `max={available}` and shows red border if exceeded
 *   - Caller can use `hasValidationErrors` exported helper to block submit
 */
import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Plus, Minus, Search, FileQuestion, Box, Beaker, Library } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useMachinePieces, PickerPiece } from '@/hooks/useInventory';
import { SectionDivider, BlueprintBackground } from './primitives';

export interface PlannedRow {
  piece_id: number;
  piece_name: string;
  piece_reference: string;
  quantity_planned: string;
  unit: string;
  stock_quantity: number;
  min_stock: number | null;
  available_quantity: number;
}

export interface PendingDraft {
  name: string;
  quantity: string;
  unit: string;
  category: string;
  notes: string;
}

interface PiecePickerProps {
  machineId: number | null;
  selectedRows: PlannedRow[];
  pendingDrafts: PendingDraft[];
  onSelectedChange: (rows: PlannedRow[]) => void;
  onPendingChange: (drafts: PendingDraft[]) => void;
  readonly?: boolean;
}

/** Returns true when any planned row has qty > available — caller should block submit. */
export function hasValidationErrors(rows: PlannedRow[]): boolean {
  return rows.some((r) => {
    const q = Number(r.quantity_planned);
    return !Number.isFinite(q) || q <= 0 || q > r.available_quantity;
  });
}

export function PiecePicker({
  machineId,
  selectedRows,
  pendingDrafts,
  onSelectedChange,
  onPendingChange,
  readonly = false,
}: PiecePickerProps) {
  const [search, setSearch] = useState('');
  const { data, loading } = useMachinePieces(machineId, search.length >= 2 ? search : undefined);

  // Stable per-row React keys for pendingDrafts, independent of the plain-data
  // shape sent to the API (pendingDrafts itself carries no id field).
  const pendingDraftKeysRef = useRef<string[]>([]);

  const selectedIds = useMemo(() => new Set(selectedRows.map((r) => r.piece_id)), [selectedRows]);

  const addPiece = useCallback(
    (piece: PickerPiece) => {
      if (selectedIds.has(piece.id)) return;
      const avail = Number(piece.available_quantity ?? piece.stock_quantity ?? 0);
      if (avail <= 0) return; // hard block at picker level — rupture
      onSelectedChange([
        ...selectedRows,
        {
          piece_id: piece.id,
          piece_name: piece.name,
          piece_reference: piece.reference,
          quantity_planned: '1',
          unit: piece.default_unit || 'pcs',
          stock_quantity: Number(piece.stock_quantity ?? 0),
          min_stock: piece.min_stock,
          available_quantity: avail,
        },
      ]);
    },
    [selectedRows, selectedIds, onSelectedChange],
  );

  const removePiece = useCallback(
    (piece_id: number) => {
      onSelectedChange(selectedRows.filter((r) => r.piece_id !== piece_id));
    },
    [selectedRows, onSelectedChange],
  );

  const updateQty = useCallback(
    (piece_id: number, qty: string) => {
      onSelectedChange(
        selectedRows.map((r) => (r.piece_id === piece_id ? { ...r, quantity_planned: qty } : r)),
      );
    },
    [selectedRows, onSelectedChange],
  );

  const addPendingDraft = useCallback(() => {
    pendingDraftKeysRef.current.push(crypto.randomUUID());
    onPendingChange([
      ...pendingDrafts,
      { name: '', quantity: '1', unit: 'pcs', category: '', notes: '' },
    ]);
  }, [pendingDrafts, onPendingChange]);

  const updateDraft = useCallback(
    (index: number, patch: Partial<PendingDraft>) => {
      onPendingChange(pendingDrafts.map((d, i) => (i === index ? { ...d, ...patch } : d)));
    },
    [pendingDrafts, onPendingChange],
  );

  const removeDraft = useCallback(
    (index: number) => {
      pendingDraftKeysRef.current.splice(index, 1);
      onPendingChange(pendingDrafts.filter((_, i) => i !== index));
    },
    [pendingDrafts, onPendingChange],
  );

  const compatible = data?.compatible ?? [];
  const consumables = data?.consumables ?? [];
  const other = data?.other ?? [];

  const anyExceeds = selectedRows.some(
    (r) => Number(r.quantity_planned) > r.available_quantity,
  );

  return (
    <div className="relative space-y-4">
      <BlueprintBackground className="rounded-md" />

      {/* Selected rows — plan summary at top */}
      {selectedRows.length > 0 && (
        <div className="relative space-y-2 rounded-md border border-emerald-500/30 bg-emerald-950/20 p-3">
          <SectionDivider
            label={`Plan d'intervention · ${selectedRows.length}`}
            tone={anyExceeds ? 'danger' : 'success'}
          />
          <div className="space-y-1.5">
            {selectedRows.map((row) => {
              const q = Number(row.quantity_planned);
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
                    value={row.quantity_planned}
                    onChange={(e) => updateQty(row.piece_id, e.target.value)}
                    disabled={readonly}
                    className={`w-20 h-7 font-mono tabular-nums text-right bg-slate-950/60 focus-visible:ring-emerald-400/50 ${
                      exceeds ? 'text-red-300 border-red-500/60' : 'text-emerald-300 border-emerald-500/30'
                    }`}
                    aria-label={`Quantité prévue pour ${row.piece_name}`}
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
                  {!readonly && (
                    <button
                      type="button"
                      onClick={() => removePiece(row.piece_id)}
                      className="ml-1 text-red-400/70 hover:text-red-300 transition-colors"
                      title="Retirer"
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                  )}
                </div>
              );
            })}
            {anyExceeds && (
              <p className="text-[11px] text-red-400 font-mono mt-1 px-1 flex items-center gap-1">
                <span className="text-red-500">▲</span>
                Une ou plusieurs quantités dépassent le stock disponible — corriger avant de soumettre.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Pending drafts (uncatalogued) */}
      {pendingDrafts.length > 0 && (
        <div className="relative space-y-2 rounded-md border border-amber-500/30 bg-amber-950/20 p-3">
          <SectionDivider label={`Pièces non-cataloguées · ${pendingDrafts.length}`} tone="warning" />
          <div className="space-y-1.5">
            {pendingDrafts.map((d, i) => {
              if (!pendingDraftKeysRef.current[i]) pendingDraftKeysRef.current[i] = crypto.randomUUID();
              return (
              <div
                key={pendingDraftKeysRef.current[i]}
                className="grid grid-cols-12 gap-1.5 items-center rounded bg-slate-900/60 border border-amber-500/20 px-2 py-1.5"
              >
                <Input
                  placeholder="Nom de la pièce"
                  value={d.name}
                  onChange={(e) => updateDraft(i, { name: e.target.value })}
                  className="col-span-5 h-7 text-sm bg-slate-950/60 border-amber-500/30 placeholder:text-amber-300/40 focus-visible:ring-amber-400/50"
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
                  className="col-span-2 h-7 font-mono tabular-nums text-right text-amber-300 bg-slate-950/60 border-amber-500/30 focus-visible:ring-amber-400/50"
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
            ⚠ ces pièces nécessiteront validation admin · placeholder créé dès soumission
          </p>
        </div>
      )}

      {!readonly && (
        <>
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

          {/* Compatible */}
          {Boolean(machineId) && (
            <PickerSection
              icon={<Box className="h-3 w-3" />}
              label="Pièces compatibles machine"
              count={compatible.length}
              tone="success"
              loading={loading}
            >
              {compatible.map((p) => (
                <PieceRow
                  key={p.id}
                  piece={p}
                  selected={selectedIds.has(p.id)}
                  onAdd={() => addPiece(p)}
                />
              ))}
            </PickerSection>
          )}

          {/* Consumables */}
          {consumables.length > 0 && (
            <PickerSection
              icon={<Beaker className="h-3 w-3" />}
              label="Consommables"
              count={consumables.length}
              tone="default"
              loading={false}
            >
              {consumables.map((p) => (
                <PieceRow
                  key={p.id}
                  piece={p}
                  selected={selectedIds.has(p.id)}
                  onAdd={() => addPiece(p)}
                />
              ))}
            </PickerSection>
          )}

          {/* Search-all results */}
          {search.length >= 2 && other.length > 0 && (
            <PickerSection
              icon={<Library className="h-3 w-3" />}
              label={`Catalogue complet · "${search}"`}
              count={other.length}
              tone="default"
              loading={loading}
            >
              {other.map((p) => (
                <PieceRow
                  key={p.id}
                  piece={p}
                  selected={selectedIds.has(p.id)}
                  onAdd={() => addPiece(p)}
                />
              ))}
            </PickerSection>
          )}

          {/* Pending-piece quick add */}
          <div className="relative rounded-md border border-dashed border-amber-500/30 bg-amber-950/10 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-amber-400/80">
                <FileQuestion className="h-4 w-4" />
                <div>
                  <p className="text-xs font-mono uppercase tracking-wider">Pièce non-cataloguée ?</p>
                  <p className="text-[10px] text-amber-400/50 mt-0.5">
                    Saisie libre · validation admin requise après l'intervention
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
                AJOUTER
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Subcomponents ───────────────────────────────────────────────────────

interface PickerSectionProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  tone: 'default' | 'success' | 'warning';
  loading: boolean;
  children: React.ReactNode;
}

function PickerSection({ icon, label, count, tone, loading, children }: PickerSectionProps) {
  const borderColor = {
    default: 'border-blue-500/20',
    success: 'border-emerald-500/20',
    warning: 'border-amber-500/20',
  }[tone];

  return (
    <div className={`relative rounded-md border ${borderColor} bg-slate-950/40 overflow-hidden`}>
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-current/10 bg-slate-900/60">
        <span className="text-blue-400/80">{icon}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-blue-300/80">{label}</span>
        <span className="font-mono text-[10px] text-blue-400/50 tabular-nums">[{count}]</span>
        {loading && <span className="ml-auto text-blue-400/50 text-[10px] font-mono animate-pulse">…</span>}
      </div>
      <div className="max-h-48 overflow-y-auto divide-y divide-blue-500/5">
        {React.Children.count(children) === 0 && (
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

function PieceRow({ piece, selected, onAdd }: PieceRowProps) {
  const stockQty = Number(piece.stock_quantity ?? 0);
  const avail = Number(piece.available_quantity ?? stockQty);
  const reserved = Number(piece.reserved_quantity ?? 0);
  const rupture = avail <= 0;
  const lowAvail = !rupture && piece.min_stock != null && avail < Number(piece.min_stock);

  const disabled = selected || rupture;

  return (
    <button
      type="button"
      onClick={onAdd}
      disabled={disabled}
      className={`w-full flex items-center gap-3 px-3 py-1.5 text-left transition-colors ${
        selected
          ? 'bg-emerald-500/5 cursor-default'
          : rupture
            ? 'bg-red-950/20 cursor-not-allowed opacity-60'
            : 'hover:bg-blue-500/5 cursor-pointer'
      }`}
      aria-disabled={disabled}
      title={rupture ? `Rupture · ${avail} ${piece.default_unit} disponibles` : undefined}
    >
      <span
        className={`font-mono text-[10px] tracking-wider min-w-[80px] ${
          selected ? 'text-emerald-400/60' : rupture ? 'text-red-400/80' : 'text-blue-400/80'
        }`}
      >
        {piece.reference}
      </span>
      <span
        className={`flex-1 text-sm truncate ${
          selected ? 'text-emerald-300/80' : rupture ? 'text-red-300/70 line-through' : 'text-blue-100'
        }`}
      >
        {piece.name}
      </span>

      {/* Availability vs raw stock */}
      <span className="font-mono text-[10px] tabular-nums whitespace-nowrap">
        {rupture ? (
          <span className="text-red-400 font-bold uppercase tracking-wider">RUPTURE</span>
        ) : (
          <>
            <span className={`font-semibold ${lowAvail ? 'text-amber-400' : 'text-emerald-300'}`}>{avail}</span>
            <span className="text-blue-400/60 ml-0.5">{piece.default_unit}</span>
            {reserved > 0 && (
              <span className="text-blue-400/40 ml-1">
                /{stockQty} (résv.{reserved})
              </span>
            )}
            {lowAvail && <span className="text-amber-400 ml-1">▼</span>}
          </>
        )}
      </span>

      {selected ? (
        <span className="text-emerald-400/60 font-mono text-[10px] uppercase tracking-wider">sélectionnée</span>
      ) : rupture ? (
        <span className="text-red-400/60 font-mono text-[10px] uppercase tracking-wider">indispo</span>
      ) : (
        <Plus className="h-3.5 w-3.5 text-blue-400/60" />
      )}
    </button>
  );
}
