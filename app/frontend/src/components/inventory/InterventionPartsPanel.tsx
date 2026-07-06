/**
 * InterventionPartsPanel — read-only summary of pieces tied to an intervention.
 *
 * Surfaces three buckets from the canonical /by-wo endpoint:
 *   1. required (reservations — planned + reserved qty + approval state)
 *   2. consumed (actual movements at completion)
 *   3. pending  (uncatalogued items awaiting admin review)
 *
 * Used in WO detail / intervention detail screens.
 */
import { Loader2, Boxes, Package, FileQuestion, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useInterventionParts,
  useInterventionPartsByWO,
  RequiredPiece,
  ConsumedPiece,
  PendingPiece,
} from '@/hooks/useInventory';
import { SectionDivider, formatNum, relTime } from './primitives';

interface InterventionPartsPanelProps {
  /** Provide either interventionId OR workOrderId — not both. */
  interventionId?: number | null;
  workOrderId?: number | null;
}

export function InterventionPartsPanel({ interventionId, workOrderId }: Readonly<InterventionPartsPanelProps>) {
  // Two hook variants — pick the one matching the caller's key
  const byItv = useInterventionParts(interventionId ?? null);
  const byWo  = useInterventionPartsByWO(interventionId ? null : workOrderId ?? null);
  const data = interventionId ? byItv.data : byWo.data;
  const loading = interventionId ? byItv.loading : byWo.loading;
  const error = interventionId ? byItv.error : byWo.error;

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-6 text-blue-400 font-mono text-xs">
          <Loader2 className="w-4 h-4 animate-spin" />
          chargement des pièces…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-rose-400 font-mono text-xs">
          erreur: {error}
        </CardContent>
      </Card>
    );
  }

  if (!data || (data.required.length === 0 && data.consumed.length === 0 && data.pending.length === 0)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Boxes className="h-4 w-4 text-blue-400" />
            Pièces de l'intervention
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-blue-400/60 font-mono text-[11px] uppercase tracking-wider">
            aucune pièce structurée associée
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Boxes className="h-4 w-4 text-blue-400" />
            Pièces de l'intervention
          </span>
          {data.parts_approved === true && (
            <Badge className="bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 font-mono text-[9px] uppercase tracking-wider">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              Pièces validées
            </Badge>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-5">
        {data.required.length > 0 && <RequiredSection items={data.required} />}
        {data.consumed.length > 0 && <ConsumedSection items={data.consumed} />}
        {data.pending.length > 0 && <PendingSection items={data.pending} />}
      </CardContent>
    </Card>
  );
}

// ─── Sections ────────────────────────────────────────────────────────────

function RequiredSection({ items }: Readonly<{ items: RequiredPiece[] }>) {
  return (
    <section className="space-y-2">
      <SectionDivider label={`Pièces requises · ${items.length}`} tone="default" />
      <div className="space-y-1.5">
        {items.map((rp) => {
          const reserved = Number(rp.quantity_reserved);
          return (
            <div
              key={rp.id}
              className="flex items-center gap-3 rounded border border-blue-500/20 bg-slate-950/40 px-3 py-2"
            >
              <Package className="h-3.5 w-3.5 text-blue-400 shrink-0" />
              <span className="font-mono text-[10px] tracking-wider text-blue-400 min-w-[72px]">
                {rp.piece_reference}
              </span>
              <span className="flex-1 text-sm text-blue-100 truncate">{rp.piece_name}</span>
              <span className="font-mono text-xs tabular-nums">
                <span className="text-emerald-400">prévu </span>
                <span className="text-emerald-300 font-semibold">{formatNum(rp.quantity_planned)}</span>
                <span className="text-emerald-400/60 mx-0.5">{rp.unit}</span>
                {reserved > 0 && (
                  <>
                    <span className="text-blue-500/60 mx-1">·</span>
                    <span className="text-blue-300">réservé </span>
                    <span className="text-blue-200 font-semibold">{formatNum(reserved)}</span>
                  </>
                )}
              </span>
              <ApprovalBadge approved={rp.approved} reserved={reserved} />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ConsumedSection({ items }: Readonly<{ items: ConsumedPiece[] }>) {
  return (
    <section className="space-y-2">
      <SectionDivider label={`Pièces consommées · ${items.length}`} tone="success" />
      <div className="space-y-1.5">
        {items.map((cp) => {
          const used = Number(cp.quantity_used);
          const ret  = Number(cp.quantity_returned);
          const wst  = Number(cp.quantity_wasted);
          return (
            <div
              key={cp.id}
              className="flex items-center gap-3 rounded border border-emerald-500/20 bg-emerald-950/15 px-3 py-2"
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
              <span className="font-mono text-[10px] tracking-wider text-blue-400 min-w-[72px]">
                {cp.piece_reference}
              </span>
              <span className="flex-1 text-sm text-blue-100 truncate">{cp.piece_name}</span>
              <span className="font-mono text-xs tabular-nums flex items-center gap-2">
                {used > 0 && <span className="text-emerald-300">used <span className="font-bold">{formatNum(used)}</span></span>}
                {ret > 0  && <span className="text-blue-300">retour <span className="font-bold">{formatNum(ret)}</span></span>}
                {wst > 0  && <span className="text-rose-300">rebut <span className="font-bold">{formatNum(wst)}</span></span>}
                <span className="text-blue-400/60 ml-0.5">{cp.unit}</span>
              </span>
              <Badge className="font-mono text-[9px] uppercase tracking-wider bg-emerald-500/15 text-emerald-300 border border-emerald-500/40">
                {cp.disposition}
              </Badge>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function PendingSection({ items }: Readonly<{ items: PendingPiece[] }>) {
  return (
    <section className="space-y-2">
      <SectionDivider label={`Pièces non-cataloguées · ${items.length}`} tone="warning" />
      <div className="space-y-1.5">
        {items.map((pp) => (
          <div
            key={pp.id}
            className="flex items-center gap-3 rounded border border-amber-500/30 bg-amber-950/10 px-3 py-2"
          >
            <FileQuestion className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <span className="flex-1 text-sm text-amber-100 truncate">{pp.name}</span>
            {pp.category && (
              <Badge variant="secondary" className="font-mono text-[9px] uppercase tracking-wider bg-slate-800/80 text-amber-200">
                {pp.category}
              </Badge>
            )}
            <span className="font-mono text-xs tabular-nums text-amber-300">
              <span className="font-semibold">{formatNum(pp.quantity)}</span>
              <span className="opacity-60 ml-0.5">{pp.unit}</span>
            </span>
            <span className="text-[10px] text-amber-400/60 font-mono">{relTime(pp.created_at)}</span>
            <Badge className={`font-mono text-[9px] uppercase tracking-wider border ${pendingStatusClass(pp.status)}`}>
              {pp.status}
            </Badge>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Small helpers ──────────────────────────────────────────────────────

function ApprovalBadge({ approved, reserved }: Readonly<{ approved: boolean | null; reserved: number }>) {
  if (reserved > 0) {
    return (
      <Badge className="bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 font-mono text-[9px] uppercase tracking-wider">
        Réservé
      </Badge>
    );
  }
  if (approved === false) {
    return (
      <Badge className="bg-rose-500/15 text-rose-300 border border-rose-500/40 font-mono text-[9px] uppercase tracking-wider">
        <AlertTriangle className="w-3 h-3 mr-1" />
        Refusé
      </Badge>
    );
  }
  return (
    <Badge className="bg-blue-500/15 text-blue-300 border border-blue-500/40 font-mono text-[9px] uppercase tracking-wider">
      En attente
    </Badge>
  );
}

function pendingStatusClass(status: string): string {
  switch (status) {
    case 'PENDING_REVIEW': return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
    case 'MATCHED':        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
    case 'CREATED':        return 'bg-blue-500/15 text-blue-300 border-blue-500/40';
    case 'REJECTED':       return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
    default:               return 'bg-slate-500/15 text-slate-300 border-slate-500/40';
  }
}
