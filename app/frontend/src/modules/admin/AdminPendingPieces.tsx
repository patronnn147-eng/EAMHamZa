/**
 * AdminPendingPieces — review queue for uncatalogued piece submissions.
 *
 * Aesthetic: workshop precision. Blueprint-grid backgrounds on cards.
 * Tier suggestions render as stacked-chevron badges. Each card supports
 * three terminal actions: MATCH (link to existing piece), CREATE (new
 * catalog entry), REJECT (with reason). All actions are one-click after
 * the admin selects a tier suggestion.
 */
import { useMemo, useState } from 'react';
import {
  PackageSearch,
  CheckCircle2,
  PlusCircle,
  XCircle,
  ImageIcon,
  Loader2,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import {
  usePendingPieces,
  usePieceSuggestions,
  PendingPiece,
  PieceSuggestion,
} from '@/hooks/useInventory';
import {
  SectionDivider,
  TierBadge,
  BlueprintBackground,
  formatNum,
  relTime,
} from '@/components/inventory/primitives';

type StatusFilter = 'PENDING_REVIEW' | 'MATCHED' | 'CREATED' | 'REJECTED' | 'ALL';

export default function AdminPendingPieces() {
  const [filter, setFilter] = useState<StatusFilter>('PENDING_REVIEW');
  const { data, total, loading, error, matchPending, rejectPending, createFromPending } =
    usePendingPieces(filter === 'ALL' ? '' : filter);
  const { toast } = useToast();

  const [rejectTarget, setRejectTarget] = useState<PendingPiece | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [createTarget, setCreateTarget] = useState<PendingPiece | null>(null);

  const handleMatch = async (pending: PendingPiece, suggestion: PieceSuggestion) => {
    try {
      await matchPending(pending.id, suggestion.piece_id);
      toast({
        title: 'Pièce associée',
        description: `${pending.name} → ${suggestion.name}`,
      });
    } catch (e) {
      toast({
        title: 'Échec association',
        description: e instanceof Error ? e.message : 'Erreur',
        variant: 'destructive',
      });
    }
  };

  const handleReject = async () => {
    if (!rejectTarget || rejectReason.trim().length < 3) return;
    try {
      await rejectPending(rejectTarget.id, rejectReason.trim());
      toast({ title: 'Rejetée', description: rejectTarget.name });
      setRejectTarget(null);
      setRejectReason('');
    } catch (e) {
      toast({
        title: 'Échec rejet',
        description: e instanceof Error ? e.message : 'Erreur',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-5">
      {/* Page header */}
      <header className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-['DM_Sans'] text-2xl font-semibold text-white flex items-center gap-2.5">
            <PackageSearch className="h-7 w-7 text-amber-400" />
            File d'attente · pièces non-cataloguées
          </h1>
          <p className="mt-1 text-sm text-blue-300/70 font-mono tracking-wide">
            <span className="text-amber-400 font-semibold tabular-nums">{total}</span> soumission(s)
            · validation requise pour intégration au catalogue
          </p>
        </div>

        <Tabs value={filter} onValueChange={(v) => setFilter(v as StatusFilter)}>
          <TabsList className="bg-slate-900/60 border border-blue-500/20">
            <TabsTrigger value="PENDING_REVIEW" className="font-mono text-[11px] uppercase tracking-wider data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-300">
              En attente
            </TabsTrigger>
            <TabsTrigger value="MATCHED" className="font-mono text-[11px] uppercase tracking-wider data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-300">
              Associées
            </TabsTrigger>
            <TabsTrigger value="CREATED" className="font-mono text-[11px] uppercase tracking-wider data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-300">
              Créées
            </TabsTrigger>
            <TabsTrigger value="REJECTED" className="font-mono text-[11px] uppercase tracking-wider data-[state=active]:bg-red-500/20 data-[state=active]:text-red-300">
              Rejetées
            </TabsTrigger>
            <TabsTrigger value="ALL" className="font-mono text-[11px] uppercase tracking-wider data-[state=active]:bg-blue-500/20">
              Tout
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </header>

      {/* Loading / error / empty */}
      {loading && data.length === 0 && (
        <div className="flex items-center justify-center py-16 text-blue-400/60 font-mono text-sm">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          chargement…
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-500/40 bg-red-950/30 px-4 py-3 text-red-300 font-mono text-sm">
          erreur: {error}
        </div>
      )}

      {!loading && data.length === 0 && (
        <EmptyState filter={filter} />
      )}

      {/* List */}
      <div className="space-y-4">
        {data.map((p, idx) => (
          <PendingCard
            key={p.id}
            pending={p}
            index={idx}
            onMatch={(s) => handleMatch(p, s)}
            onReject={() => setRejectTarget(p)}
            onCreate={() => setCreateTarget(p)}
          />
        ))}
      </div>

      {/* Reject dialog */}
      <Dialog open={rejectTarget != null} onOpenChange={(o) => { if (!o) setRejectTarget(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <XCircle className="h-5 w-5" />
              Rejeter la soumission
            </DialogTitle>
            <DialogDescription className="text-blue-300/70">
              {rejectTarget?.name} · {formatNum(rejectTarget?.quantity)} {rejectTarget?.unit}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label htmlFor="reject-reason" className="font-mono text-[11px] uppercase tracking-wider text-red-400/80">
              Motif (min. 3 caractères)
            </label>
            <Textarea
              id="reject-reason"
              placeholder="Doublon, soumission incorrecte, etc."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="bg-slate-950/60 border-red-500/30"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectTarget(null)}>Annuler</Button>
            <Button
              onClick={handleReject}
              disabled={rejectReason.trim().length < 3}
              className="bg-red-700 hover:bg-red-600"
            >
              Rejeter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create dialog */}
      {createTarget && (
        <CreateFromPendingDialog
          pending={createTarget}
          onCancel={() => setCreateTarget(null)}
          onCreated={async (payload) => {
            try {
              await createFromPending(createTarget.id, payload);
              toast({ title: 'Pièce créée', description: payload.name as string });
              setCreateTarget(null);
            } catch (e) {
              toast({
                title: 'Échec création',
                description: e instanceof Error ? e.message : 'Erreur',
                variant: 'destructive',
              });
            }
          }}
        />
      )}
    </div>
  );
}

// ─── PendingCard ─────────────────────────────────────────────────────────

interface PendingCardProps {
  pending: PendingPiece;
  index: number;
  onMatch: (suggestion: PieceSuggestion) => void;
  onReject: () => void;
  onCreate: () => void;
}

function PendingCard({ pending, index, onMatch, onReject, onCreate }: Readonly<PendingCardProps>) {
  const isPending = pending.status === 'PENDING_REVIEW';
  const { data: suggestions, loading: suggestLoading } = usePieceSuggestions(
    isPending ? pending.name : '',
  );

  const statusColor = useMemo(() => {
    switch (pending.status) {
      case 'PENDING_REVIEW': return { border: 'border-amber-500/40', glow: 'shadow-amber-500/10', text: 'text-amber-300', bg: 'bg-amber-950/10' };
      case 'MATCHED':        return { border: 'border-emerald-500/40', glow: 'shadow-emerald-500/10', text: 'text-emerald-300', bg: 'bg-emerald-950/10' };
      case 'CREATED':        return { border: 'border-blue-500/40', glow: 'shadow-blue-500/10', text: 'text-blue-300', bg: 'bg-blue-950/10' };
      case 'REJECTED':       return { border: 'border-red-500/40', glow: 'shadow-red-500/10', text: 'text-red-300', bg: 'bg-red-950/10' };
      default: return { border: 'border-slate-700', glow: '', text: 'text-slate-300', bg: 'bg-slate-900/40' };
    }
  }, [pending.status]);

  return (
    <article
      className={`relative rounded-lg border-l-2 ${statusColor.border} ${statusColor.bg} overflow-hidden shadow-lg ${statusColor.glow}`}
      style={{
        animation: `slide-fade-in 0.4s ease-out ${index * 80}ms both`,
      }}
    >
      <BlueprintBackground />

      {/* Top-bar: identity + status */}
      <header className="relative flex items-center justify-between gap-4 px-4 py-3 border-b border-current/10">
        <div className="flex items-center gap-3">
          {/* Sequential id */}
          <span className="font-mono text-[10px] text-blue-400/50 tracking-wider tabular-nums">
            #{String(pending.id).padStart(4, '0')}
          </span>
          <h3 className="font-['DM_Sans'] text-lg font-semibold text-white truncate">
            {pending.name}
          </h3>
          {pending.category && (
            <Badge variant="secondary" className="font-mono text-[9px] uppercase tracking-wider bg-slate-800/80 text-blue-300 border-blue-500/20">
              {pending.category}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="font-mono tabular-nums text-blue-300">
            <span className="opacity-60">qté </span>
            <span className="text-amber-300 font-semibold">{formatNum(pending.quantity)}</span>
            <span className="ml-0.5 opacity-60">{pending.unit}</span>
          </span>
          <span className="text-blue-400/40">·</span>
          <span className="font-mono text-blue-400/60 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {relTime(pending.created_at)}
          </span>
          {pending.submitted_by_name && (
            <>
              <span className="text-blue-400/40">·</span>
              <span className="font-mono text-blue-400/60">par {pending.submitted_by_name}</span>
            </>
          )}
          <Badge className={`ml-2 font-mono text-[10px] uppercase tracking-wider ${statusColor.bg} ${statusColor.text} border ${statusColor.border}`}>
            {pending.status}
          </Badge>
        </div>
      </header>

      {/* Body */}
      <div className="relative grid grid-cols-12 gap-4 px-4 py-3">
        {/* LEFT: photo placeholder + notes */}
        <div className="col-span-3 space-y-2">
          <div className="aspect-square rounded border border-blue-500/20 bg-slate-950/60 flex items-center justify-center">
            {pending.photo_object_key ? (
              <span className="text-blue-300 text-xs">📷 photo</span>
            ) : (
              <ImageIcon className="h-8 w-8 text-blue-500/30" />
            )}
          </div>
          {Boolean(pending.intervention_id) && (
            <p className="font-mono text-[10px] tracking-wider text-blue-400/60">
              ↳ intervention #{pending.intervention_id}
            </p>
          )}
          {pending.notes && (
            <p className="text-xs text-blue-300/80 italic border-l-2 border-blue-500/30 pl-2 leading-snug">
              "{pending.notes}"
            </p>
          )}
        </div>

        {/* RIGHT: suggestions + actions */}
        <div className="col-span-9 space-y-3">
          {/* Action: status-dependent */}
          {pending.status === 'MATCHED' && pending.matched_piece_name && (
            <div className="flex items-center gap-2 text-sm text-emerald-300">
              <CheckCircle2 className="h-4 w-4" />
              Associée à : <span className="font-mono text-emerald-200">{pending.matched_piece_name}</span>
              <span className="font-mono text-[10px] text-emerald-400/60 ml-1">
                ({pending.reviewed_at ? relTime(pending.reviewed_at) : ''})
              </span>
            </div>
          )}
          {pending.status === 'CREATED' && pending.matched_piece_name && (
            <div className="flex items-center gap-2 text-sm text-blue-300">
              <PlusCircle className="h-4 w-4" />
              Pièce créée : <span className="font-mono text-blue-200">{pending.matched_piece_name}</span>
            </div>
          )}
          {pending.status === 'REJECTED' && pending.rejection_reason && (
            <div className="flex items-start gap-2 text-sm text-red-300/80">
              <XCircle className="h-4 w-4 mt-0.5" />
              <div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-red-400">motif</span>
                <p className="italic">"{pending.rejection_reason}"</p>
              </div>
            </div>
          )}

          {/* Pending review: show suggestions + 3 actions */}
          {isPending && (
            <>
              <SectionDivider label="Suggestions fuzzy-match" tone="default" />

              {suggestLoading && (
                <p className="font-mono text-[10px] text-blue-400/50 animate-pulse">
                  recherche dans le catalogue…
                </p>
              )}

              {!suggestLoading && suggestions.length === 0 && (
                <p className="font-mono text-[11px] text-amber-400/60">
                  aucune correspondance dans le catalogue · création requise
                </p>
              )}

              {!suggestLoading && suggestions.length > 0 && (
                <ul className="space-y-1.5">
                  {suggestions.map((s) => (
                    <li
                      key={s.piece_id}
                      className="flex items-center gap-2 rounded border border-slate-700/60 bg-slate-950/40 px-2.5 py-1.5 hover:border-emerald-500/40 hover:bg-emerald-500/5 transition-colors group"
                    >
                      <TierBadge tier={s.tier} similarity={s.similarity} machineMatch={s.machine_match} />
                      <span className="font-mono text-[10px] text-blue-400/70 tracking-wider min-w-[80px]">
                        {s.reference}
                      </span>
                      <span className="flex-1 text-sm text-blue-100 truncate">{s.name}</span>
                      {s.category && (
                        <span className="font-mono text-[9px] uppercase text-slate-400 tracking-wider">
                          {s.category}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => onMatch(s)}
                        className="ml-2 flex items-center gap-1 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-emerald-300 hover:bg-emerald-500/20 transition-all opacity-70 group-hover:opacity-100"
                      >
                        ASSOCIER
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {/* Bottom action bar */}
              <div className="flex items-center gap-2 pt-2 border-t border-blue-500/10">
                <Button
                  type="button"
                  size="sm"
                  onClick={onCreate}
                  className="bg-blue-700 hover:bg-blue-600 font-mono text-[11px] tracking-wider"
                >
                  <PlusCircle className="h-3.5 w-3.5 mr-1.5" />
                  CRÉER NOUVELLE PIÈCE
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={onReject}
                  className="border-red-500/40 text-red-300 hover:bg-red-500/10 font-mono text-[11px] tracking-wider"
                >
                  <XCircle className="h-3.5 w-3.5 mr-1.5" />
                  REJETER
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </article>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────

function EmptyState({ filter }: Readonly<{ filter: StatusFilter }>) {
  const message = {
    PENDING_REVIEW: 'aucune soumission en attente · file vide',
    MATCHED: 'aucune pièce associée',
    CREATED: 'aucune pièce créée depuis la file',
    REJECTED: 'aucun rejet enregistré',
    ALL: 'aucune soumission enregistrée',
  }[filter];

  return (
    <div className="relative rounded-lg border border-dashed border-blue-500/30 bg-slate-950/40 py-16 text-center">
      <BlueprintBackground />
      <div className="relative">
        <PackageSearch className="h-10 w-10 mx-auto mb-3 text-blue-500/40" />
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-blue-400/60">
          {message}
        </p>
      </div>
    </div>
  );
}

// ─── Create dialog ───────────────────────────────────────────────────────

interface CreateFromPendingDialogProps {
  pending: PendingPiece;
  onCancel: () => void;
  onCreated: (payload: Record<string, unknown>) => Promise<void>;
}

function CreateFromPendingDialog({ pending, onCancel, onCreated }: Readonly<CreateFromPendingDialogProps>) {
  const [form, setForm] = useState({
    reference: '',
    name: pending.name,
    description: pending.notes || '',
    unit_price: '',
    category: pending.category || '',
    min_stock: '5',
    is_consumable: pending.unit !== 'pcs',
    default_unit: pending.unit,
  });

  const handleCreate = async () => {
    await onCreated({
      reference: form.reference.trim(),
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      unit_price: form.unit_price ? Number(form.unit_price) : undefined,
      category: form.category.trim() || undefined,
      min_stock: Number(form.min_stock) || 5,
      is_consumable: form.is_consumable,
      default_unit: form.default_unit,
    });
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onCancel(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-blue-300">
            <PlusCircle className="h-5 w-5" />
            Créer pièce depuis soumission
          </DialogTitle>
          <DialogDescription className="font-mono text-[11px] tracking-wider text-blue-400/70">
            #{String(pending.id).padStart(4, '0')} · {pending.name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Référence *</span>
              <Input
                value={form.reference}
                onChange={(e) => setForm({ ...form, reference: e.target.value })}
                placeholder="REF-XXX"
                className="font-mono"
              />
            </label>
            <label className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Nom *</span>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
          </div>

          <label className="space-y-1 block">
            <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Description</span>
            <Input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>

          <div className="grid grid-cols-4 gap-3">
            <label className="space-y-1 col-span-2">
              <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Catégorie</span>
              <Input
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
            </label>
            <label className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Prix €</span>
              <Input
                type="number"
                step="0.01"
                value={form.unit_price}
                onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
                className="font-mono tabular-nums"
              />
            </label>
            <label className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Stock min.</span>
              <Input
                type="number"
                value={form.min_stock}
                onChange={(e) => setForm({ ...form, min_stock: e.target.value })}
                className="font-mono tabular-nums"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-blue-400">Unité par défaut</span>
              <Input
                value={form.default_unit}
                onChange={(e) => setForm({ ...form, default_unit: e.target.value })}
                className="font-mono"
              />
            </label>
            <label className="flex items-center gap-2 pt-5 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_consumable}
                onChange={(e) => setForm({ ...form, is_consumable: e.target.checked })}
                className="rounded border-blue-500/40 bg-slate-900"
              />
              <span className="font-mono text-[11px] uppercase tracking-wider text-blue-300">
                Consommable
              </span>
            </label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>Annuler</Button>
          <Button
            onClick={handleCreate}
            disabled={!form.reference.trim() || !form.name.trim()}
            className="bg-blue-700 hover:bg-blue-600"
          >
            Créer & associer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
