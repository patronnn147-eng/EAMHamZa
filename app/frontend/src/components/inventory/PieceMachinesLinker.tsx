/**
 * PieceMachinesLinker — admin dialog to link a piece to machines.
 *
 * Hybrid scope strategy:
 *   - Default view: "Machines en activité" (operationally relevant)
 *     fetched from /inventory/pieces/machines-scope
 *   - Toggle: "Toutes les machines" (entire fleet) — admin override
 *
 * Already-linked machines are pre-checked. Clicking a checkbox immediately
 * fires the link/unlink endpoint (optimistic update with rollback on error).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Link2, X, AlertTriangle, Cog, Filter, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { SectionDivider, BlueprintBackground } from './primitives';

const apiBase = import.meta.env.VITE_API_BASE_URL || '';

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

interface MachineEntry {
  id: number;
  nom: string;
  zone?: string | null;
  statut?: string | null;
}

interface PieceMachinesLinkerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pieceId: number;
  pieceName: string;
  pieceReference: string;
}

export function PieceMachinesLinker({
  open,
  onOpenChange,
  pieceId,
  pieceName,
  pieceReference,
}: PieceMachinesLinkerProps) {
  const { toast } = useToast();
  const [scopeMode, setScopeMode] = useState<'in-scope' | 'all'>('in-scope');
  const [machines, setMachines] = useState<MachineEntry[]>([]);
  const [linkedIds, setLinkedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set());

  // Fetch on open or scope-mode change
  const fetchData = useCallback(async () => {
    if (!open) return;
    setLoading(true);
    try {
      const url =
        scopeMode === 'in-scope'
          ? `${apiBase}/api/v1/inventory/pieces/scope/machines`
          : `${apiBase}/api/v1/entities/machines?size=500`;

      const [scopeResp, linkedResp] = await Promise.all([
        fetch(url, { headers: getAuthHeaders() }),
        fetch(`${apiBase}/api/v1/inventory/pieces/${pieceId}/machines`, {
          headers: getAuthHeaders(),
        }),
      ]);

      if (scopeResp.ok) {
        const body = await scopeResp.json();
        const items: MachineEntry[] = (body.items || []).map((m: any) => ({
          id: m.id,
          nom: m.nom,
          zone: m.zone,
          statut: m.statut,
        }));
        setMachines(items);
      }
      if (linkedResp.ok) {
        const body = await linkedResp.json();
        setLinkedIds(new Set<number>(body.machine_ids || []));
      }
    } catch (e) {
      toast({
        title: 'Erreur',
        description: e instanceof Error ? e.message : 'Chargement échoué',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [open, pieceId, scopeMode, toast]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // Filter machines by search term (client-side, ≤500 items)
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return machines;
    return machines.filter(
      (m) =>
        m.nom.toLowerCase().includes(q) ||
        (m.zone || '').toLowerCase().includes(q) ||
        String(m.id).includes(q),
    );
  }, [machines, search]);

  // Optimistic toggle: link or unlink
  const toggleLink = useCallback(
    async (machine: MachineEntry) => {
      const wasLinked = linkedIds.has(machine.id);
      setBusyIds((prev) => new Set(prev).add(machine.id));

      // Optimistic
      setLinkedIds((prev) => {
        const next = new Set(prev);
        if (wasLinked) next.delete(machine.id);
        else next.add(machine.id);
        return next;
      });

      try {
        const url = wasLinked
          ? `${apiBase}/api/v1/inventory/pieces/${pieceId}/machines/${machine.id}`
          : `${apiBase}/api/v1/inventory/pieces/${pieceId}/machines`;

        const resp = await fetch(url, {
          method: wasLinked ? 'DELETE' : 'POST',
          headers: getAuthHeaders(),
          body: wasLinked ? undefined : JSON.stringify({ machine_id: machine.id }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        toast({
          title: wasLinked ? 'Lien retiré' : 'Lien créé',
          description: `${pieceReference} ${wasLinked ? '✕' : '↔'} ${machine.nom}`,
        });
      } catch (e) {
        // Rollback
        setLinkedIds((prev) => {
          const next = new Set(prev);
          if (wasLinked) next.add(machine.id);
          else next.delete(machine.id);
          return next;
        });
        toast({
          title: 'Erreur',
          description: e instanceof Error ? e.message : 'Opération échouée',
          variant: 'destructive',
        });
      } finally {
        setBusyIds((prev) => {
          const next = new Set(prev);
          next.delete(machine.id);
          return next;
        });
      }
    },
    [linkedIds, pieceId, pieceReference, toast],
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-blue-100">
            <Link2 className="h-5 w-5 text-emerald-400" />
            Lier la pièce aux machines
          </DialogTitle>
          <DialogDescription className="font-mono text-xs tracking-wide text-blue-400/70 flex items-center gap-2 mt-1">
            <span className="text-blue-300">{pieceReference}</span>
            <span className="opacity-40">·</span>
            <span>{pieceName}</span>
          </DialogDescription>
        </DialogHeader>

        {/* Scope toggle + search */}
        <div className="flex items-center gap-2 flex-wrap py-2 border-y border-blue-500/10">
          <div className="flex rounded-md border border-blue-500/30 bg-slate-950/60 p-0.5 text-xs font-mono">
            <button
              type="button"
              onClick={() => setScopeMode('in-scope')}
              className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
                scopeMode === 'in-scope'
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : 'text-blue-400 hover:text-blue-200'
              }`}
            >
              <Filter className="h-3 w-3" />
              EN ACTIVITÉ
            </button>
            <button
              type="button"
              onClick={() => setScopeMode('all')}
              className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
                scopeMode === 'all'
                  ? 'bg-blue-500/20 text-blue-200'
                  : 'text-blue-400 hover:text-blue-200'
              }`}
            >
              <Layers className="h-3 w-3" />
              TOUTES
            </button>
          </div>

          <Input
            placeholder="Rechercher machine / zone / id…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 h-8 text-xs bg-slate-950/40 border-blue-500/20"
          />
        </div>

        {/* Help text */}
        <p className="font-mono text-[10px] tracking-wider text-blue-400/60 leading-relaxed">
          {scopeMode === 'in-scope' ? (
            <>
              <span className="text-emerald-400">⊙</span> machines avec planning actif OU activité OT récente (90j)
            </>
          ) : (
            <>
              <span className="text-blue-400">⊕</span> catalogue complet · utiliser uniquement si nécessaire
            </>
          )}
        </p>

        {/* List */}
        <div className="relative flex-1 overflow-hidden rounded border border-blue-500/15 bg-slate-950/40">
          <BlueprintBackground />
          <div className="relative h-full overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center gap-2 py-12 text-blue-400/60 font-mono text-xs">
                <Loader2 className="h-4 w-4 animate-spin" />
                chargement…
              </div>
            )}

            {!loading && filtered.length === 0 && (
              <div className="flex flex-col items-center justify-center gap-2 py-12 text-blue-400/40">
                <AlertTriangle className="h-6 w-6" />
                <p className="font-mono text-[11px] uppercase tracking-wider">
                  {search ? 'aucun résultat' : 'liste vide'}
                </p>
              </div>
            )}

            {!loading && filtered.length > 0 && (
              <ul className="divide-y divide-blue-500/5">
                {filtered.map((m) => {
                  const linked = linkedIds.has(m.id);
                  const busy = busyIds.has(m.id);
                  return (
                    <li
                      key={m.id}
                      className={`flex items-center gap-3 px-3 py-2 transition-colors ${
                        linked ? 'bg-emerald-500/5' : 'hover:bg-blue-500/5'
                      }`}
                    >
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => toggleLink(m)}
                        className={`shrink-0 flex items-center justify-center w-5 h-5 rounded border-2 transition-all ${
                          linked
                            ? 'bg-emerald-500 border-emerald-500'
                            : 'border-blue-500/40 hover:border-emerald-400/60'
                        } ${busy ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                        aria-label={linked ? `Retirer le lien à ${m.nom}` : `Lier à ${m.nom}`}
                      >
                        {busy ? (
                          <Loader2 className="h-3 w-3 animate-spin text-white" />
                        ) : linked ? (
                          <svg viewBox="0 0 20 20" fill="white" className="h-3 w-3">
                            <path fillRule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 9.7a1 1 0 1 1 1.4-1.4L8.5 12 15.3 5.3a1 1 0 0 1 1.4 0Z" />
                          </svg>
                        ) : null}
                      </button>

                      <Cog className="h-3.5 w-3.5 text-blue-400/60 shrink-0" />

                      <span className="font-mono text-[10px] text-blue-400/60 tabular-nums min-w-[40px]">
                        #{m.id}
                      </span>

                      <span className={`flex-1 text-sm truncate ${linked ? 'text-emerald-200' : 'text-blue-100'}`}>
                        {m.nom}
                      </span>

                      {m.zone && (
                        <Badge variant="secondary" className="font-mono text-[9px] uppercase tracking-wider bg-slate-800/60 text-blue-300 border-blue-500/20">
                          {m.zone}
                        </Badge>
                      )}

                      {m.statut && (
                        <Badge className={`font-mono text-[9px] uppercase tracking-wider ${
                          m.statut === 'OPERATIONNELLE' || m.statut === 'EN_MARCHE'
                            ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                            : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                        } border`}>
                          {m.statut}
                        </Badge>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Footer: summary */}
        <div className="flex items-center justify-between gap-2 pt-2">
          <SectionDivider
            label={`${linkedIds.size} liée(s) · ${filtered.length} affichée(s)`}
            tone={linkedIds.size > 0 ? 'success' : 'default'}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="font-mono text-xs tracking-wider">
            <X className="h-3.5 w-3.5 mr-1.5" />
            Fermer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
